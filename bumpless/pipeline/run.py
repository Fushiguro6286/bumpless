"""Orchestrates one migration run. Every step emits step_started / progress / step_finished / error events."""

import json
import time
import traceback
import uuid
from contextlib import asynccontextmanager

from bumpless.llm.client import LLM, BudgetExceeded
from bumpless.pipeline import baseline, characterize, coverage, edit, intake, output, plan, review, scan, verify
from bumpless.pipeline.context import RunContext
from bumpless.recipes import store
from bumpless.research import freshness
from bumpless.research.rulebook import norm_url
from bumpless.research.tavily_client import Tavily
from bumpless.sandbox.base import get_executor
from bumpless.settings import settings
from bumpless.storage import db

STEPS = ["intake", "baseline", "research", "characterize", "plan", "edit", "verify", "coverage", "review",
         "output", "learn"]
CHAR = "tests._bumpless"


@asynccontextmanager
async def step(ctx: RunContext, name: str):
    t0 = time.perf_counter()
    ctx.emit("step_started", step=name)
    yield
    ctx.emit("step_finished", step=name, duration_s=round(time.perf_counter() - t0, 2),
             cost_usd=round(ctx.llm.spent, 6))


def final_status(ctx: RunContext) -> str:
    after = ctx.tests.get("after")
    if not after:
        return "failed"
    remaining = verify.new_failures(ctx, after)
    repo_failing = [t for t in remaining if not t.startswith(CHAR)]
    if not remaining and after.passed >= ctx.tests["old"].passed and not ctx.review.get("violations"):
        return "green"
    if not repo_failing and after.passed >= ctx.tests["old"].passed:
        return "partial"  # repo tests green, but recorded behavior changed or a guardrail fired
    before = [t for t in verify.new_failures(ctx, ctx.tests["new_before"]) if not t.startswith(CHAR)]
    improved = len(repo_failing) < len(before) or after.repo_passed > ctx.tests["new_before"].repo_passed
    return "partial" if improved else "failed"


def tavily_usage(ctx: RunContext) -> dict:
    rules = ctx.rulebook.rules if ctx.rulebook else []
    calls = []
    for c in ctx.tavily.calls:
        urls = {norm_url(u) for u in c["urls_json"]}
        calls.append({"kind": c["kind"], "query": c["query"], "results": c["n_results"], "cached": bool(c["cached"]),
                      "urls": c["urls_json"][:20], "rules": [r.id for r in rules if r.source_url in urls]})
    return {"calls": len(calls), "by_kind": {k: sum(c["kind"] == k for c in calls) for k in ("search", "extract", "map")},
            "log": calls}


def build_result(ctx: RunContext, source: str, routing: str, error: str | None, t_start: float) -> dict:
    return {
        "run_id": ctx.run_id, "status": ctx.status, "error": error, "source": source, "package": ctx.package,
        "target": ctx.target, "routing": routing, "executor": ctx.executor.name, "workspace": str(ctx.workspace),
        "old_version": ctx.old_version, "new_version": ctx.new_version,
        "tests": {k: v.summary() for k, v in ctx.tests.items()},
        "rulebook": ctx.rulebook.model_dump(by_alias=True) if ctx.rulebook else None,
        "recipe_reused": ctx.recipe_reused,
        "plan": ctx.plan.model_dump() if ctx.plan else None,
        "characterization": ctx.characterization, "coverage": ctx.coverage, "review": ctx.review,
        "hunks": [h.__dict__ for h in ctx.hunks], "escalations": ctx.escalations,
        "manual_review": list(dict.fromkeys(ctx.manual_review)),
        "cost": {"total_usd": ctx.llm.spent, "by_tier": ctx.llm.by_tier, "llm_calls": len(ctx.llm.calls)},
        "tavily": tavily_usage(ctx),
        "duration_s": round(time.time() - t_start, 1),
    }


async def run_migration(source: str, package: str, target: str, routing: str = "tiered",
                        executor: str | None = None, run_id: str | None = None, open_pr: bool = False,
                        ref: str | None = None) -> dict:
    run_id = run_id or uuid.uuid4().hex[:10]
    t_start = time.time()
    db.insert("runs", {"id": run_id, "created_at": t_start, "repo": source, "package": package, "target": target,
                       "routing": routing, "status": "running", "result_json": None})
    ex = get_executor(executor or settings.executor)
    ctx = RunContext(run_id=run_id, workspace=None, package=package, target=target,
                     llm=LLM(run_id, routing), tavily=Tavily(run_id), executor=ex)
    ctx.emit("run_started", source=source, package=package, target=target, routing=routing, executor=ex.name)
    error, out = None, {}
    try:
        async with step(ctx, "intake"):
            ctx.workspace = intake.prepare_workspace(source, run_id, ref)
            ctx.pins = intake.find_pins(ctx.workspace, package)
            ctx.install_cmds = intake.install_commands(ctx.workspace)
            ctx.repo_names = review.repo_defined_names(ctx.workspace)
            ctx.progress("intake", f"Workspace ready; {len(ctx.pins)} version pin(s) for {package}",
                         pins=[p.__dict__ for p in ctx.pins])

        async with step(ctx, "baseline"):
            await baseline.baseline(ctx)

        async with step(ctx, "research"):
            usage = scan.usage_identifiers(ctx.workspace, package)
            ctx.rulebook, ctx.recipe_reused = await freshness.get_rulebook(ctx, usage)
            for r in ctx.rulebook.rules:
                if not r.verified:
                    ctx.manual_review.append(f"Unverified rule {r.id} not applied: {r.title} ({r.source_url})")
            ctx.emit("rulebook", step="research", rulebook=ctx.rulebook.model_dump(by_alias=True))
            verified = sum(r.verified for r in ctx.rulebook.rules)
            if not ctx.recipe_reused:
                ctx.progress("research", f"Rulebook built from {ctx.rulebook.official_pages} official pages: "
                             f"{len(ctx.rulebook.rules)} rules, {verified} verified")

        async with step(ctx, "characterize"):
            ctx.characterization = await characterize.characterize(ctx)

        rules = [r for r in ctx.rulebook.rules if r.verified]  # unverified rules are never applied
        async with step(ctx, "plan"):
            ctx.scan = scan.scan(ctx.workspace, rules, package)
            ctx.plan = await plan.plan(ctx, rules)
            ctx.manual_review += ctx.plan.manual_review
            ctx.emit("plan", step="plan", plan=ctx.plan.model_dump())
            ctx.progress("plan", f"{len(ctx.plan.files)} files to migrate: {ctx.plan.summary}")

        async with step(ctx, "edit"):
            await edit.edit_all(ctx, rules)
            pins = intake.apply_pin_bumps(ctx.workspace, ctx.pins, package, target)
            ctx.progress("edit", f"{len(ctx.hunks)} edits applied; {len(pins)} version pin(s) bumped", pins=pins)

        async with step(ctx, "verify"):
            await baseline.install(ctx)  # the bumped pins must resolve
            ctx.tests["after"] = await verify.verify_and_repair(ctx)
            for t in verify.new_failures(ctx, ctx.tests["after"]):
                if t.startswith(CHAR):
                    ctx.manual_review.append(f"Behavior changed vs {package} {ctx.old_version}: {t.split('::')[-1]}")

        async with step(ctx, "coverage"):
            ctx.coverage = await coverage.measure(ctx)

        async with step(ctx, "review"):
            ctx.review = await review.review(ctx)

        ctx.status = final_status(ctx)
        async with step(ctx, "output"):
            out = output.output(ctx, source, build_result(ctx, source, routing, None, t_start), open_pr)
            ctx.progress("output", f"PR opened: {out['pr_url']}" if out["pr_url"] else
                         f"Patch + report written ({out['pr_skipped_reason']})", **out)

        async with step(ctx, "learn"):
            if ctx.status != "failed":
                recipe, changed = store.save(ctx.rulebook, run_id)
                ctx.progress("learn", f"Recipe {recipe.package} {recipe.from_}→{recipe.to} v{recipe.recipe_version} "
                             + ("updated" if changed else "unchanged"), recipe_version=recipe.recipe_version)
    except BudgetExceeded as e:
        error = str(e)
        ctx.emit("error", message=error)
    except Exception as e:  # surface a readable error; full traceback goes to the event log
        error = f"{type(e).__name__}: {e}"
        ctx.emit("error", message=error, traceback=traceback.format_exc()[-4000:])
    finally:
        await ex.close()

    if error:
        ctx.status = "failed"
    result = build_result(ctx, source, routing, error, t_start) | {"output": out}
    if ctx.rulebook:
        store.record_run(ctx.rulebook, run_id, ctx.recipe_reused, ctx.status, ctx.llm.spent)
    with db.connect() as conn:
        conn.execute("UPDATE runs SET status=?, result_json=? WHERE id=?", (ctx.status, json.dumps(result), run_id))
    ctx.emit("run_finished", status=ctx.status, error=error, cost_usd=ctx.llm.spent, duration_s=result["duration_s"])
    return result

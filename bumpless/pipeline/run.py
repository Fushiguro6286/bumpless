"""Orchestrates one migration run. Every step emits step_started / progress / step_finished / error events."""

import json
import time
import traceback
import uuid
from contextlib import asynccontextmanager

from bumpless.llm.client import LLM, BudgetExceeded
from bumpless.pipeline import baseline, edit, intake, plan, scan, verify
from bumpless.pipeline.context import RunContext
from bumpless.research import rulebook, verify_sources
from bumpless.research.tavily_client import Tavily
from bumpless.sandbox.base import get_executor
from bumpless.settings import settings
from bumpless.storage import db

STEPS = ["intake", "baseline", "research", "plan", "edit", "verify", "output"]


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
    if not remaining and after.passed >= ctx.tests["old"].passed:
        return "green"
    before = len(verify.new_failures(ctx, ctx.tests["new_before"]))
    return "partial" if len(remaining) < before or after.passed > ctx.tests["new_before"].passed else "failed"


async def run_migration(source: str, package: str, target: str, routing: str = "tiered",
                        executor: str | None = None, run_id: str | None = None) -> dict:
    run_id = run_id or uuid.uuid4().hex[:10]
    t_start = time.time()
    db.insert("runs", {"id": run_id, "created_at": t_start, "repo": source, "package": package, "target": target,
                       "routing": routing, "status": "running", "result_json": None})
    ex = get_executor(executor or settings.executor)
    ctx = RunContext(run_id=run_id, workspace=None, package=package, target=target,
                     llm=LLM(run_id, routing), tavily=Tavily(run_id), executor=ex)
    ctx.emit("run_started", source=source, package=package, target=target, routing=routing, executor=ex.name)
    error = None
    try:
        async with step(ctx, "intake"):
            ctx.workspace = intake.prepare_workspace(source, run_id)
            ctx.pins = intake.find_pins(ctx.workspace, package)
            ctx.install_cmds = intake.install_commands(ctx.workspace)
            ctx.progress("intake", f"Workspace ready; {len(ctx.pins)} version pin(s) for {package}",
                         pins=[p.__dict__ for p in ctx.pins])

        async with step(ctx, "baseline"):
            await baseline.baseline(ctx)

        async with step(ctx, "research"):
            usage = scan.usage_identifiers(ctx.workspace, package)
            ctx.rulebook = await rulebook.research(ctx, usage)
            await verify_sources.verify_rules(ctx, ctx.rulebook.rules)
            for r in ctx.rulebook.rules:
                if not r.verified:
                    ctx.manual_review.append(f"Unverified rule {r.id} not applied: {r.title} ({r.source_url})")
            ctx.emit("rulebook", step="research", rulebook=ctx.rulebook.model_dump(by_alias=True))
            ctx.progress("research", f"Rulebook built from {ctx.rulebook.official_pages} official pages: "
                         f"{len(ctx.rulebook.rules)} rules, {sum(r.verified for r in ctx.rulebook.rules)} verified")

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

        async with step(ctx, "output"):
            patch = ctx.workspace / ".bumpless" / "bumpless.patch"
            patch.write_text(verify.git_diff(ctx) + "\n", encoding="utf-8")
            ctx.progress("output", f"Patch written to {patch}")
    except BudgetExceeded as e:
        error = str(e)
    except Exception as e:  # surface a readable error; full traceback goes to the event log
        error = f"{type(e).__name__}: {e}"
        ctx.emit("error", message=error, traceback=traceback.format_exc()[-4000:])
    finally:
        await ex.close()

    ctx.status = "failed" if error else final_status(ctx)
    result = {
        "run_id": run_id, "status": ctx.status, "error": error, "package": package, "target": target,
        "routing": routing, "executor": ex.name, "workspace": str(ctx.workspace),
        "old_version": ctx.old_version, "new_version": ctx.new_version,
        "tests": {k: v.summary() for k, v in ctx.tests.items()},
        "rulebook": ctx.rulebook.model_dump(by_alias=True) if ctx.rulebook else None,
        "plan": ctx.plan.model_dump() if ctx.plan else None,
        "hunks": [h.__dict__ for h in ctx.hunks], "escalations": ctx.escalations,
        "manual_review": ctx.manual_review,
        "cost": {"total_usd": ctx.llm.spent, "by_tier": ctx.llm.by_tier, "llm_calls": len(ctx.llm.calls)},
        "tavily": {"calls": len(ctx.tavily.calls),
                   "by_kind": {k: sum(c["kind"] == k for c in ctx.tavily.calls) for k in ("search", "extract", "map")}},
        "duration_s": round(time.time() - t_start, 1),
    }
    with db.connect() as conn:
        conn.execute("UPDATE runs SET status=?, result_json=? WHERE id=?", (ctx.status, json.dumps(result), run_id))
    ctx.emit("run_finished", status=ctx.status, error=error, cost_usd=ctx.llm.spent, duration_s=result["duration_s"])
    return result

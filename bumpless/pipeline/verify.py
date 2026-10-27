"""Step 6: run tests on the new version; Ultra diagnoses failures and repairs, with Tavily lookups for
errors the rulebook does not explain."""

import re

from bumpless.llm import prompts
from bumpless.llm.schemas import Rule
from bumpless.pipeline.baseline import run_tests
from bumpless.pipeline.context import Hunk, RunContext, TestRun
from bumpless.pipeline.edit import apply_block, new_errors, parse_blocks
from bumpless.pipeline.plan import rules_text
from bumpless.pipeline.review import guardrail_violations
from bumpless.research.rulebook import keep_cited, number_rules

MAX_REPAIR_ITERATIONS = 4
MAX_FILES_CHARS = 60_000


def new_failures(ctx: RunContext, run: TestRun) -> list[str]:
    pre = set(ctx.tests["old"].failing)
    return [t for t in run.failing if t not in pre]


def git_diff(ctx: RunContext, *args: str) -> str:
    import git
    return git.Repo(ctx.workspace).git.diff(*args)


def relevant_files(ctx: RunContext, output: str) -> str:
    changed = git_diff(ctx, "--name-only").splitlines()
    mentioned = re.findall(r"([\w./-]+\.py)", output)
    paths, seen = [], set()
    for p in changed + mentioned:
        p = p.replace("\\", "/").removeprefix("/work/")
        if p not in seen and (ctx.workspace / p).is_file() and ".bumpless" not in p:
            seen.add(p)
            paths.append(p)
    blob, used = [], 0
    for p in paths:
        text = (ctx.workspace / p).read_text(encoding="utf-8", errors="replace")
        if used + len(text) > MAX_FILES_CHARS:
            break
        used += len(text)
        blob.append(f"{p}\n```python\n{text}\n```")
    return "\n\n".join(blob)


async def learn_from_error(ctx: RunContext, error: str) -> list[Rule]:
    """Search the exact error message, summarize, and turn it into cited rules."""
    from bumpless.research.rulebook import summarize_pages, synthesize
    query = f'"{error[:200]}" {ctx.package} {ctx.new_version}'
    hits = await ctx.tavily.search(query, search_depth="advanced", max_results=5, include_raw_content="markdown")
    src = ctx.sources
    before = set(src.pages)
    for h in hits:
        src.add(h["url"], h.get("raw_content") or h.get("content") or "")
    fresh = type(src)(src.domains, src.repos)
    fresh.pages = {u: t for u, t in src.pages.items() if u not in before}
    if not fresh.pages:
        return []
    notes = await summarize_pages(ctx, fresh, ctx.from_major, ctx.to_major)
    rules = await synthesize(ctx, fresh, notes, ctx.from_major, ctx.to_major, [error], max_rules=3)
    rules = number_rules(keep_cited(rules, src), start=len(ctx.rulebook.rules) + 1)
    for r in rules:
        r.learned_from_run = ctx.run_id
    return rules


async def verify_and_repair(ctx: RunContext) -> TestRun:
    looked_up: set[str] = set()
    run = await run_tests(ctx)
    for it in range(1, MAX_REPAIR_ITERATIONS + 1):
        failing = new_failures(ctx, run)
        ctx.progress("verify", f"Tests: {run.passed} passed, {len(failing)} failing", tests=run.summary(),
                     iteration=it - 1)
        if not failing:
            break
        reply = await ctx.llm.chat("diagnose", [{"role": "user", "content": _diagnose_prompt(ctx, run, failing)}],
                                   step="repair", max_tokens=16000)
        lookup = _field(reply, "LOOKUP")
        if lookup and lookup.upper() != "NONE" and lookup not in looked_up:
            looked_up.add(lookup)
            ctx.progress("repair", f"Unknown error, searching: {lookup[:120]}", lookup=lookup)
            learned = await learn_from_error(ctx, lookup)
            if learned:
                ctx.rulebook.rules.extend(learned)
                ctx.emit("rules_learned", step="repair", rules=[r.model_dump() for r in learned])
                reply = await ctx.llm.chat("diagnose", [{"role": "user", "content": _diagnose_prompt(
                    ctx, run, failing)}], step="repair", max_tokens=16000)
        applied = _apply_repair(ctx, reply)
        ctx.progress("repair", f"Iteration {it}: {_field(reply, 'DIAGNOSIS')[:200]} ({applied} edits)",
                     iteration=it, edits=applied)
        if not applied:
            break
        run = await run_tests(ctx)
    return run


def _diagnose_prompt(ctx: RunContext, run: TestRun, failing: list[str]) -> str:
    failures = "\n".join(failing) + "\n\n" + run.output[-12000:]
    return prompts.render("diagnose", package=ctx.package, rules=rules_text(ctx.rulebook.rules),
                          diff=git_diff(ctx)[-20000:], failures=failures, files=relevant_files(ctx, run.output),
                          **{"from": ctx.from_major, "to": ctx.to_major})


def _field(reply: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+)$", reply, re.M)
    return m.group(1).strip() if m else ""


def _apply_repair(ctx: RunContext, reply: str) -> int:
    tier = ctx.llm.calls[-1]["tier"]
    n = 0
    for b in parse_blocks(reply):
        if not b.path or not (ctx.workspace / b.path).is_file():
            continue
        f = ctx.workspace / b.path
        before = f.read_text(encoding="utf-8")
        after = apply_block(before, b.search, b.replace)
        if after is None or new_errors(b.path, before, after):
            continue
        if violations := guardrail_violations(b.path, before, after):
            ctx.progress("repair", f"Rejected repair edit: {violations[0]}", rejected=violations)
            continue
        f.write_text(after, encoding="utf-8")
        ctx.hunks.append(Hunk(b.path, b.rule_id, b.search, b.replace, tier, repaired=True))
        n += 1
    return n

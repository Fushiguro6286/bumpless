"""Step 4b: Ultra plans the migration from the scan + rulebook."""

import json

from bumpless.llm import prompts
from bumpless.llm.schemas import Plan, PlanFile, Rule
from bumpless.pipeline.context import RunContext


def rules_text(rules: list[Rule]) -> str:
    return "\n".join(f"{r.id}: {r.title}\n  old: {r.old_pattern}\n  new: {r.new_pattern}\n  notes: {r.notes}\n"
                     + (f"  docs say: {r.evidence}\n" if r.evidence else "") + f"  source: {r.source_url}"
                     for r in rules)


async def plan(ctx: RunContext, rules: list[Rule]) -> Plan:
    scan_view = {p: v["rules"] for p, v in ctx.scan.items() if v["rules"]}
    importers = [p for p, v in ctx.scan.items() if v["imports"] or v.get("uses")]
    result = await ctx.llm.chat("plan", [{"role": "user", "content": prompts.render(
        "plan", package=ctx.package, rules=rules_text(rules), scan=json.dumps(scan_view, indent=1),
        importers=", ".join(importers) or "(none)", **{"from": ctx.from_major, "to": ctx.to_major})}],
        step="plan", schema=Plan, max_tokens=8000)
    # Keep only real files; every file the scan flagged gets edited even if the planner skipped it.
    planned = {f.path: f for f in result.files if f.path in ctx.scan}
    for path, v in ctx.scan.items():
        if path not in planned and (v["rules"] or v["imports"] or v.get("uses")):
            planned[path] = PlanFile(path=path, rule_ids=list(v["rules"]), notes="added from static scan")
    known = {r.id for r in rules}
    for f in planned.values():
        f.rule_ids = sorted(set(f.rule_ids) & known | set(ctx.scan[f.path]["rules"]) & known)
    result.files = list(planned.values())
    return result

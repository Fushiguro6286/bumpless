"""Step 7: verified change coverage (changed lines executed by >= 1 test) and per-hunk confidence."""

import json
import re
from dataclasses import dataclass, field

from bumpless.pipeline.baseline import JUNIT
from bumpless.pipeline.context import RunContext
from bumpless.pipeline.verify import git_diff

GENERATED = "tests/_bumpless/"
RCFILE = """[run]
relative_files = True
source = .
omit = .bumpless/*
    tests/_bumpless/_harness.py
"""
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass
class DiffHunk:
    path: str
    start: int  # first line in the new file
    added: dict[int, str] = field(default_factory=dict)  # new line number -> text
    removed: list[str] = field(default_factory=list)


def parse_diff(diff: str) -> list[DiffHunk]:
    hunks, path, cur, line = [], None, None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@") and path:
            m = _HUNK.match(raw)
            line = int(m.group(1))
            cur = DiffHunk(path, line)
            hunks.append(cur)
        elif cur is None or raw.startswith(("---", "diff ", "index ")):
            continue
        elif raw.startswith("+"):
            cur.added[line] = raw[1:]
            line += 1
        elif raw.startswith("-"):
            cur.removed.append(raw[1:])
        elif raw.startswith(" "):
            line += 1
    return [h for h in hunks if h.path]


def change_coverage(hunks: list[DiffHunk], cov: dict) -> tuple[int, int, dict[str, set[int]]]:
    """(executed changed lines, executable changed lines, executed lines per file)."""
    files = cov.get("files", {})
    executed_by_file = {p.replace("\\", "/"): set(d["executed_lines"]) for p, d in files.items()}
    executable_by_file = {p.replace("\\", "/"): set(d["executed_lines"]) | set(d["missing_lines"])
                          for p, d in files.items()}
    hit = total = 0
    for h in hunks:
        exe = executable_by_file.get(h.path, set())
        ran = executed_by_file.get(h.path, set())
        for n in h.added:
            if n in exe:
                total += 1
                hit += n in ran
    return hit, total, executed_by_file


def _provenance(ctx: RunContext, h: DiffHunk):
    """The edit block that produced this diff hunk: prefer blocks citing a known rule, then the most
    overlapping lines, then the latest (an uncited whole-file rewrite must not hide the cited edit)."""
    added = {x.strip() for x in h.added.values() if x.strip()}
    known = {r.id for r in ctx.rulebook.rules} if ctx.rulebook else set()
    best, best_key = None, None
    for i, e in enumerate(ctx.hunks):
        overlap = len({x.strip() for x in e.replace.splitlines() if x.strip()} & added) if e.path == h.path else 0
        key = (e.rule_id in known, overlap, i)
        if overlap and (best_key is None or key > best_key):
            best, best_key = e, key
    return best


def confidence(ctx: RunContext, h: DiffHunk, executed: set[int], executable: set[int]) -> tuple[str, list[str]]:
    rules = {r.id: r for r in ctx.rulebook.rules} if ctx.rulebook else {}
    exe_lines = [n for n in h.added if n in executable]
    ran = bool(exe_lines) and all(n in executed for n in exe_lines)
    prov = _provenance(ctx, h)
    rule = rules.get(prov.rule_id) if prov else None
    why = []
    if exe_lines and not ran:
        why.append("changed lines not executed by any test")
    if not rule:
        why.append("no rule from the rulebook cited")
    elif not rule.verified:
        why.append(f"rule {rule.id} is unverified")
    if why:
        return "Low", why
    if not exe_lines:  # pure deletion or non-executable lines: nothing a test could execute
        return "Medium", ["no executable changed lines"]
    medium = []
    if prov.escalated:
        medium.append(f"needed escalation to {prov.model_tier}")
    if prov.repaired:
        medium.append("added by the repair loop")
    if not rule.source_official:
        medium.append("source is not official")
    return ("Medium", medium) if medium else ("High", ["executed by tests; verified official rule; first-try edit"])


async def measure(ctx: RunContext) -> dict:
    (ctx.workspace / ".bumpless" / "coveragerc").write_text(RCFILE, encoding="utf-8")
    r = await ctx.executor.run(ctx.workspace, [
        f"python -m coverage run --rcfile=.bumpless/coveragerc -m pytest -q -p no:cacheprovider "
        f"--junitxml={JUNIT} || true",
        "python -m coverage json --rcfile=.bumpless/coveragerc -o .bumpless/coverage.json",
    ], timeout_s=900)
    path = ctx.workspace / ".bumpless" / "coverage.json"
    if r.exit_code != 0 or not path.exists():
        ctx.progress("coverage", "Coverage could not be measured")
        return {"measured": False, "error": r.output[-1500:]}
    cov = json.loads(path.read_text(encoding="utf-8"))
    pins = {p.file for p in ctx.pins}
    hunks = [h for h in parse_diff(git_diff(ctx, "HEAD", "-U0"))
             if h.path.endswith(".py") and not h.path.startswith(GENERATED)]
    hit, total, executed_by_file = change_coverage(hunks, cov)
    files = cov.get("files", {})
    out_hunks = []
    for h in hunks:
        d = next((v for p, v in files.items() if p.replace("\\", "/") == h.path), None)
        exe = set(d["executed_lines"]) | set(d["missing_lines"]) if d else set()
        level, why = confidence(ctx, h, executed_by_file.get(h.path, set()), exe)
        prov = _provenance(ctx, h)
        rule = next((r for r in ctx.rulebook.rules if prov and r.id == prov.rule_id), None)
        out_hunks.append({
            "path": h.path, "start": h.start, "end": max(h.added) if h.added else h.start,
            "added": list(h.added.values()), "removed": h.removed, "confidence": level, "reasons": why,
            "rule_id": prov.rule_id if prov else None, "source_url": rule.source_url if rule else None,
            "verified": bool(rule and rule.verified), "model_tier": prov.model_tier if prov else None,
            "escalated": bool(prov and prov.escalated), "repaired": bool(prov and prov.repaired),
        })
        if level == "Low":
            ctx.manual_review.append(f"Low confidence: {h.path}:{h.start} ({'; '.join(why)})")
    pct = round(100 * hit / total, 1) if total else None
    ctx.progress("coverage", f"Verified change coverage: {hit}/{total} changed lines executed by tests"
                 + (f" ({pct}%)" if pct is not None else ""), executed=hit, total=total, percent=pct)
    return {"measured": True, "executed_changed_lines": hit, "executable_changed_lines": total, "percent": pct,
            "hunks": out_hunks, "pins_bumped": sorted(pins),
            "by_confidence": {k: sum(x["confidence"] == k for x in out_hunks) for k in ("High", "Medium", "Low")}}

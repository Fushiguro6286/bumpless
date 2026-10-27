"""Step 5: parallel per-file edits (Nano first, escalating to Super then Ultra), as search/replace blocks."""

import asyncio
import re
import subprocess
import sys
from dataclasses import dataclass

from bumpless import fsutil
from bumpless.llm import prompts
from bumpless.llm.router import tier_for
from bumpless.llm.schemas import PlanFile, Rule
from bumpless.pipeline.context import Hunk, RunContext
from bumpless.pipeline.plan import rules_text
from bumpless.pipeline.review import guardrail_violations
from bumpless.pipeline.scan import compile_hint

MAX_PARALLEL_EDITS = 8
# (escalation level, label): try Nano, retry Nano with the error, then Super, then Ultra.
ATTEMPTS = [0, 0, 1, 2]

BLOCK = re.compile(
    r"(?:^[ \t]*(?P<path>[\w./\\-]+\.py)[ \t]*\n(?:```\w*\n)?)?"
    r"^<{5,9} ?SEARCH(?:[ \t]+(?P<rule>[\w-]+))?[ \t]*\n(?P<search>.*?)^={5,9}[ \t]*\n(?P<replace>.*?)^>{5,9} ?REPLACE",
    re.S | re.M,
)


@dataclass
class Block:
    path: str | None
    rule_id: str
    search: str
    replace: str


def parse_blocks(text: str) -> list[Block]:
    return [Block(m["path"].replace("\\", "/") if m["path"] else None, m["rule"] or "UNSPECIFIED",
                  m["search"], m["replace"]) for m in BLOCK.finditer(text)]


def _indent(s: str) -> str:
    return s[: len(s) - len(s.lstrip())]


def apply_block(text: str, search: str, replace: str) -> str | None:
    """Exact match first, then a whitespace-tolerant line match (re-indenting the replacement)."""
    if search.strip() and search in text:
        return text.replace(search, replace, 1)
    # A fragment of one line (e.g. "user.json()"): replace it if it occurs exactly once.
    frag = search.strip()
    if frag and "\n" not in frag and "\n" not in replace.strip() and text.count(frag) == 1:
        return text.replace(frag, replace.strip(), 1)
    s_lines = search.rstrip("\n").split("\n")
    while s_lines and not s_lines[0].strip():
        s_lines.pop(0)
    if not s_lines:
        return None
    lines = text.split("\n")
    want = [x.strip() for x in s_lines]
    for i in range(len(lines) - len(s_lines) + 1):
        if [x.strip() for x in lines[i:i + len(s_lines)]] == want:
            have, had = _indent(lines[i]), _indent(s_lines[0])
            rep = [have + x[len(had):] if x.startswith(had) else x
                   for x in replace.rstrip("\n").split("\n")] if replace.strip() else []
            return "\n".join(lines[:i] + rep + lines[i + len(s_lines):])
    return None


def static_errors(path: str, src: str) -> list[str]:
    """Syntax errors + ruff's fatal checks (undefined names, invalid syntax)."""
    try:
        compile(src, path, "exec")
    except SyntaxError as e:
        return [f"SyntaxError line {e.lineno}: {e.msg}"]
    r = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--select", "E9,F63,F7,F82", "--output-format", "concise",
         "--no-cache", "--stdin-filename", path, "-"],
        input=src, capture_output=True, text=True, encoding="utf-8",
    )
    return [line.split(":", 3)[-1].strip() for line in r.stdout.splitlines() if re.match(r".+:\d+:\d+:", line)]


def new_errors(path: str, before: str, after: str) -> list[str]:
    old = set(static_errors(path, before))
    return [e for e in static_errors(path, after) if e not in old]


def apply_blocks(path: str, text: str, blocks: list[Block]) -> tuple[str, list[str]]:
    errors = []
    for b in blocks:
        out = apply_block(text, b.search, b.replace)
        if out is None and b.replace.strip() and b.replace.strip() in text and b.search.strip() not in text:
            continue  # already applied (models sometimes repeat a block)
        if out is None:
            errors.append(f"SEARCH block for {b.rule_id} did not match the file:\n{b.search[:300]}")
        else:
            text = out
    return text, errors


def _where(text: str, hints: dict, ids: list[str]) -> str:
    """'- R031 still matches line 12: @root_validator' for each rule whose detection pattern still matches."""
    lines = text.split("\n")
    out = []
    for rid in ids:
        if m := hints[rid].search(text):
            n = text.count("\n", 0, m.start())
            out.append(f"- {rid} still matches line {n + 1}: {lines[n].strip()}")
    return "\n".join(out)


async def edit_file(ctx: RunContext, pf: PlanFile, rules: list[Rule], sem: asyncio.Semaphore) -> list[Hunk]:
    path = ctx.workspace / pf.path
    original = current = fsutil.read(path)
    feedback = reply = ""
    notes = (pf.notes or "") + (f" Static scan matched: {', '.join(pf.rule_ids)}." if pf.rule_ids else "")
    # Completeness check: after edits apply, the matched rules' detection patterns should no longer match.
    hints = {r.id: rx for r in rules if r.id in pf.rule_ids and (rx := compile_hint(r))}
    hunks: list[Hunk] = []
    residual: list[str] = []
    async with sem:
        for n, esc in enumerate(ATTEMPTS):
            tier = tier_for("edit", ctx.llm.routing, esc)
            if n >= 2:
                ctx.escalations.append({"path": pf.path, "tier": tier, "reason": feedback[:300],
                                        "previous_reply": reply[:600]})
                ctx.emit("escalation", step="edit", path=pf.path, tier=tier, message=f"{pf.path} escalated to {tier}")
            reply = await ctx.llm.chat("edit", [{"role": "user", "content": prompts.render(
                "edit", package=ctx.package, rules=rules_text(rules), notes=notes or "none", path=pf.path,
                content=current, feedback=feedback, **{"from": ctx.from_major, "to": ctx.to_major})}],
                # ~3 chars/token: room for search+replace of the whole file (~2 copies), so a degenerate reply stops early
                step="edit", escalation=esc, max_tokens=min(16000, len(current) + 2000))
            blocks = parse_blocks(reply)
            if not blocks and "NO_CHANGES" in reply:
                residual = [rid for rid, rx in hints.items() if rx.search(current)]
                if residual and n < len(ATTEMPTS) - 1:  # old patterns still match: a second (stronger) look
                    feedback = (f"\nYou replied NO_CHANGES, but the detection patterns still match:\n"
                                f"{_where(current, hints, residual)}\nMigrate these usages. Reply NO_CHANGES only if "
                                "they are truly not usages of the old API.\n")
                    continue
                if not hunks:
                    ctx.progress("edit", f"{pf.path}: no changes needed", path=pf.path, tier=tier, edits=0)
                    return []
                break  # the model considers the earlier edits complete
            new, errors = apply_blocks(pf.path, current, blocks)
            if not blocks:
                errors = ["Reply contained no edit blocks in the required format."]
            errors += new_errors(pf.path, original, new)
            errors += guardrail_violations(pf.path, original, new, ctx.repo_names)
            if errors:
                feedback = "\nYour previous attempt failed:\n" + "\n".join(errors)[:3000] + "\nFix these problems.\n"
                continue
            current = new
            hunks += [Hunk(pf.path, b.rule_id, b.search, b.replace, tier, escalated=esc > 0) for b in blocks]
            residual = [rid for rid, rx in hints.items() if rx.search(current)]
            if not residual:
                break
            feedback = (f"\nYour edits were applied (the file below includes them), but old usages remain:\n"
                        f"{_where(current, hints, residual)}\n"
                        "Migrate them too, or reply NO_CHANGES if they are not usages of the old API.\n")
    if not hunks:
        ctx.manual_review.append(f"{pf.path}: automatic edit failed after {len(ATTEMPTS)} attempts")
        ctx.progress("edit", f"{pf.path}: edit failed, needs human review", path=pf.path, failed=True)
        return []
    fsutil.write(path, current)
    if residual:
        ctx.manual_review.append(f"{pf.path}: patterns of {', '.join(residual)} still present after editing")
    ctx.progress("edit", f"{pf.path}: {len(hunks)} edits", path=pf.path, tier=hunks[-1].model_tier, edits=len(hunks))
    return hunks


async def edit_all(ctx: RunContext, rules: list[Rule]) -> None:
    sem = asyncio.Semaphore(MAX_PARALLEL_EDITS)
    files = ctx.plan.files if ctx.plan else []
    for hunks in await asyncio.gather(*[edit_file(ctx, f, rules, sem) for f in files]):
        ctx.hunks.extend(hunks)

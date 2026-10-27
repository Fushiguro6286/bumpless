"""`@bumpless` PR conversation: a reviewer comment -> revise / explain / revert, with the same guardrails as a run.

Security: only OWNER / MEMBER / COLLABORATOR comments are acted on. Comment text is only ever given to the models
as a request; it is never executed, and file targets must be files the migration changed.
"""

import asyncio
from typing import Literal

import git
from pydantic import BaseModel

from bumpless import fsutil
from bumpless.llm.schemas import PlanFile
from bumpless.pipeline import baseline, coverage, edit, review
from bumpless.pipeline.context import RunContext
from bumpless.pipeline.intake import ACTOR, ignore_scratch
from bumpless.pipeline.plan import rules_text
from bumpless.settings import settings

ALLOWED = {"OWNER", "MEMBER", "COLLABORATOR"}
TRIGGER = "@bumpless"
NOT_ALLOWED = ("Thanks for the suggestion! I only act on requests from this repository's owners, members and "
               "collaborators, so I haven't changed anything.")
HELP = ("I can **revise** a change (`@bumpless use model_dump(mode=\"json\") in app/api.py`), **explain** one "
        "(`@bumpless explain the change in app/models.py`) or **revert** a file (`@bumpless revert the change to "
        "app/utils.py`).")


class Intent(BaseModel):
    intent: Literal["revise", "explain", "revert", "other"]
    files: list[str] = []
    instruction: str = ""


class Revision(BaseModel):
    files: list[PlanFile]
    summary: str = ""


def changed_files(ws, base: str) -> list[str]:
    return [p for p in git.Repo(ws).git.diff(base, "--name-only").splitlines() if not p.startswith(".bumpless/")]


def _diff(ws, base: str, files: list[str]) -> str:
    return git.Repo(ws).git.diff(base, "--", *files) if files else ""


async def _verify(ctx: RunContext) -> dict:
    await baseline.install(ctx)
    tests = await baseline.run_tests(ctx)
    cov = await coverage.measure(ctx)
    return {"tests": tests.summary(), "coverage": {k: cov.get(k) for k in ("measured", "percent",
                                                                             "executed_changed_lines",
                                                                             "executable_changed_lines")}}


def _commit(ctx: RunContext, message: str) -> str | None:
    ignore_scratch(ctx.workspace)  # a plain `git add -A`; pathspec excludes error when the path is ignored
    repo = git.Repo(ctx.workspace)
    repo.git.add("-A")
    if not repo.is_dirty(index=True, untracked_files=False):
        return None
    return repo.index.commit(message, author=ACTOR, committer=ACTOR).hexsha[:10]


def _result_lines(v: dict, ctx: RunContext, commit: str | None, spent0: float) -> list[str]:
    t, c = v["tests"], v["coverage"]
    cov = f"{c['percent']}% ({c['executed_changed_lines']}/{c['executable_changed_lines']} changed lines)" \
        if c.get("measured") and c.get("percent") is not None else "not measured"
    untested = c.get("measured") and c.get("executable_changed_lines") and not c.get("executed_changed_lines")
    return [f"**Tests:** {t['passed']} passed, {t['failed']} failed (repository + characterization)",
            f"**Verified change coverage of this revision:** {cov}"
            + (" ⚠️ no test runs these lines, so passing tests don't prove this revision works" if untested else ""),
            f"**Commit:** `{commit}`" if commit else "**Commit:** none (nothing changed)",
            f"**Cost:** ${ctx.llm.spent - spent0:.4f} on Nemotron via {settings.provider}"]


async def handle(ctx: RunContext, comment: str, association: str, base: str, user: str = "reviewer") -> dict:
    """Returns {"acted": bool, "intent": str | None, "reply": markdown | None, ...}."""
    body = comment.strip()
    if not body.lower().startswith(TRIGGER):
        return {"acted": False, "intent": None, "reply": None}
    if association.upper() not in ALLOWED:
        return {"acted": False, "intent": None, "reply": NOT_ALLOWED}
    request = body[len(TRIGGER):].strip()
    spent0 = ctx.llm.spent
    changed = changed_files(ctx.workspace, base)
    intent = await ctx.llm.chat("comment_intent", [{"role": "user", "content": (
        "Classify this code-review comment on a dependency-migration PR. Reply with JSON only:\n"
        '{"intent": "revise|explain|revert|other", "files": ["paths the comment is about"], '
        '"instruction": "the requested change in one sentence"}\n'
        f"Files changed by the migration: {', '.join(changed) or '(none)'}\nComment: {request}")}],
        step="conversation", schema=Intent, max_tokens=3000)
    # Only files the migration touched can be targets (no path tricks, no unrelated files).
    targets = [f for f in intent.files if f in changed] or ([] if intent.files else changed)
    out = {"acted": True, "intent": intent.intent, "files": targets, "instruction": intent.instruction}

    if intent.intent == "other" or (intent.intent != "explain" and not targets):
        return out | {"acted": False, "reply": HELP if intent.intent == "other" else
                      f"I couldn't match that to a file this PR changed ({', '.join(changed)}). {HELP}"}

    if intent.intent == "explain":
        rules = ctx.rulebook.rules if ctx.rulebook else []
        text = await ctx.llm.chat("revision_plan", [{"role": "user", "content": (
            f"Explain to a code reviewer why this migration of `{ctx.package}` changed the code below. Use the "
            "rulebook; cite the rule id and its source URL for each change. Be concise (under 200 words).\n\n"
            f"Question: {request}\n\nRulebook:\n{rules_text([r for r in rules if r.verified])}\n\n"
            f"Diff:\n```diff\n{_diff(ctx.workspace, base, targets or changed)[-20000:]}\n```")}],
            step="conversation", max_tokens=4000)
        return out | {"reply": text.strip() + f"\n\n_Cost: ${ctx.llm.spent - spent0:.4f}_"}

    if intent.intent == "revert":
        repo = git.Repo(ctx.workspace)
        for f in targets:
            try:
                repo.git.checkout(base, "--", f)
            except git.GitCommandError:  # the file did not exist before the migration
                repo.git.rm("-q", "-f", "--", f)
        v = await _verify(ctx)
        commit = _commit(ctx, f"Revert Bumpless changes to {', '.join(targets)}\n\nRequested by @{user}: {request}")
        lines = [f"Reverted my changes to {', '.join(f'`{f}`' for f in targets)}, as @{user} asked.", "",
                 *_result_lines(v, ctx, commit, spent0)]
        if v["tests"]["failed"]:
            lines.append("\n⚠️ Some tests fail without this change; the old code may not work with the new version.")
        return out | {"reply": "\n".join(lines), "commit": commit, **v}

    # revise: Ultra plans the revision, Nano edits (escalating), guardrails apply to every edit.
    rules = [r for r in ctx.rulebook.rules if r.verified] if ctx.rulebook else []
    rev = await ctx.llm.chat("revision_plan", [{"role": "user", "content": (
        f"A reviewer asked for a revision of a `{ctx.package}` migration PR. Plan the edit per file: for each "
        "file, write precise instructions in `notes`. Only these files may change: "
        f"{', '.join(targets)}. Reply with JSON only: "
        '{"files": [{"path": "...", "rule_ids": [], "risk": "low", "notes": "..."}], "summary": "..."}\n\n'
        f"Request: {request}\n\nCurrent diff of those files:\n```diff\n{_diff(ctx.workspace, base, targets)[-20000:]}\n```")}],
        step="conversation", schema=Revision, max_tokens=6000)
    files = [pf for pf in rev.files if pf.path in targets]
    before = {pf.path: fsutil.read(ctx.workspace / pf.path) for pf in files}
    sem = asyncio.Semaphore(4)
    for pf in files:
        pf.notes = f"Reviewer request: {request}. Plan: {pf.notes}"
    hunks = [h for hs in await asyncio.gather(*[edit.edit_file(ctx, pf, rules, sem) for pf in files]) for h in hs]
    ctx.hunks += hunks
    if not hunks:
        return out | {"reply": "I couldn't make that change safely (my edits failed the guardrails or did not "
                               "apply), so I left the PR as it is. " + (" ".join(ctx.manual_review[-2:]))}
    v = await _verify(ctx)
    if v["tests"]["failed"]:  # never push a revision that breaks tests: undo it
        for p, text in before.items():
            fsutil.write(ctx.workspace / p, text)
        lines = [f"I tried: {rev.summary or intent.instruction}", "",
                 f"but it made {v['tests']['failed']} test(s) fail, so I undid it and pushed nothing.",
                 f"_Cost: ${ctx.llm.spent - spent0:.4f}_"]
        return out | {"reply": "\n".join(lines), "commit": None, **v}
    commit = _commit(ctx, f"Bumpless revision: {rev.summary or intent.instruction}\n\nRequested by @{user}: {request}")
    lines = [f"Done: {rev.summary or intent.instruction}", "",
             *(f"- `{h.path}` ({h.model_tier})" for h in hunks), "", *_result_lines(v, ctx, commit, spent0)]
    return out | {"reply": "\n".join(lines), "commit": commit, **v}


def context_for(ws, package: str, rulebook, run_id: str, executor: str | None = None) -> RunContext:
    """A RunContext for a revision of an existing migration in `ws` (a PR checkout or a rebuilt workspace)."""
    from bumpless.llm.client import LLM
    from bumpless.pipeline import intake
    from bumpless.sandbox.base import get_executor

    ctx = RunContext(run_id=run_id, workspace=ws, package=package, target="", llm=LLM(run_id, "tiered"),
                     tavily=None, executor=get_executor(executor or settings.executor))
    ctx.rulebook = rulebook
    ctx.pins = intake.find_pins(ws, package)
    ctx.install_cmds = intake.install_commands(ws)
    ctx.repo_names = review.repo_defined_names(ws)
    return ctx


def rebuild_workspace(fixture_dir, patch: str, run_id: str):
    """Fresh copy of the fixture with the migration patch applied as one commit (base = HEAD~1)."""
    from bumpless.pipeline import intake

    ws = intake.prepare_workspace(str(fixture_dir), run_id)
    (ws / ".bumpless" / "migration.patch").write_text(patch, encoding="utf-8")
    repo = git.Repo(ws)
    with repo.git.custom_environment(GIT_COMMITTER_NAME=ACTOR.name, GIT_COMMITTER_EMAIL=ACTOR.email):
        repo.git.am("--3way", ".bumpless/migration.patch")
    return ws

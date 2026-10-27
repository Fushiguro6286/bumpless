"""Step 8: guardrails (enforced in code on every edit and on the final diff) + an Ultra review pass."""

import ast
import re

import git
from pydantic import BaseModel

from bumpless.llm import prompts
from bumpless.llm.client import LLMOutputError
from bumpless.pipeline.context import RunContext
from bumpless.pipeline.plan import rules_text

SKIP_MARK = re.compile(r"pytest\.mark\.(?:skip|skipif|xfail)\b|pytest\.(?:skip|xfail|importorskip)\s*\("
                       r"|unittest\.skip|@skip\b|__test__\s*=\s*False")
SECRET = re.compile(r"""(?i)(?:api[_-]?key|secret|token|passw(?:or)?d)\s*[:=]\s*["'][A-Za-z0-9_\-./+]{16,}["']"""
                    r"|\b(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|tvly-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16})")
CI_PATHS = re.compile(r"^(?:\.github/|\.gitlab-ci|\.circleci/|azure-pipelines|Jenkinsfile|\.travis)")
GENERATED = "tests/_bumpless/"


def is_test_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py" or "/tests/" in f"/{path}"


def _test_stats(src: str) -> tuple[int, int, int]:
    """(asserts, test functions, trivially-true asserts)"""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return 0, 0, 0
    asserts = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    trivial = sum(isinstance(a.test, ast.Constant) and bool(a.test.value) for a in asserts)
    raises = sum(isinstance(n, ast.Attribute) and n.attr in ("raises", "warns") for n in ast.walk(tree))
    tests = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")
                for n in ast.walk(tree))
    return len(asserts) + raises, tests, trivial


def guardrail_violations(path: str, before: str, after: str) -> list[str]:
    v = []
    if CI_PATHS.match(path):
        v.append(f"{path}: CI configuration must not be edited")
    added = set(after.splitlines()) - set(before.splitlines())
    if any(SECRET.search(line) for line in added):
        v.append(f"{path}: change adds something that looks like a secret")
    if is_test_file(path) and not path.startswith(GENERATED):
        a0, t0, z0 = _test_stats(before)
        a1, t1, z1 = _test_stats(after)
        if a1 < a0:
            v.append(f"{path}: removes assertions ({a0} -> {a1}); tests may only change to use the new API")
        if t1 < t0:
            v.append(f"{path}: removes test functions ({t0} -> {t1})")
        if z1 > z0:
            v.append(f"{path}: adds an always-true assertion")
        if len(SKIP_MARK.findall(after)) > len(SKIP_MARK.findall(before)):
            v.append(f"{path}: adds skip/xfail markers")
    return v


def check_final_diff(ctx: RunContext) -> list[str]:
    """Double-check the whole diff against the baseline commit."""
    repo = git.Repo(ctx.workspace)
    allowed_non_py = {p.file for p in ctx.pins}
    violations = []
    changed = repo.git.diff("HEAD", "--name-only").splitlines() + repo.untracked_files
    for path in changed:
        if path.startswith(".bumpless/") or path.startswith(GENERATED):
            continue
        if not path.endswith(".py") and path not in allowed_non_py:
            violations.append(f"{path}: file is unrelated to the migration")
            continue
        try:
            before = repo.git.show(f"HEAD:{path}")
        except git.GitCommandError:
            before = ""
        after = (ctx.workspace / path).read_text(encoding="utf-8") if (ctx.workspace / path).exists() else ""
        violations += guardrail_violations(path, before, after)
    return violations


class Concern(BaseModel):
    path: str = ""
    issue: str


class Review(BaseModel):
    approve: bool
    summary: str = ""
    concerns: list[Concern] = []


async def review(ctx: RunContext) -> dict:
    violations = check_final_diff(ctx)
    diff = git.Repo(ctx.workspace).git.diff("HEAD", "--", ".", ":(exclude)tests/_bumpless")
    try:
        r = await ctx.llm.chat("review", [{"role": "user", "content": prompts.render(
            "review", package=ctx.package, rules=rules_text(ctx.rulebook.rules), diff=diff[-40000:],
            **{"from": ctx.from_major, "to": ctx.to_major})}], step="review", schema=Review, max_tokens=8000)
    except LLMOutputError:
        r = Review(approve=False, summary="Review model output was invalid; review manually.")
    for v in violations:
        ctx.manual_review.append(f"Guardrail: {v}")
    for c in r.concerns:
        ctx.manual_review.append(f"Review: {c.path + ': ' if c.path else ''}{c.issue}")
    ctx.progress("review", f"Guardrails: {len(violations)} violation(s). Ultra review: "
                 f"{'approved' if r.approve else 'changes flagged'}. {r.summary}")
    return {"violations": violations, "approve": r.approve and not violations, "summary": r.summary,
            "concerns": [c.model_dump() for c in r.concerns]}

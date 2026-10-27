"""Upgrade Radar: which dependencies are a major version behind, how much the repo uses them, whether a verified
recipe exists, a Super risk estimate and an estimated cost. Reads files only; never executes repo code."""

import ast
import asyncio
import re
import statistics
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel

from bumpless.llm.client import LLM, LLMOutputError
from bumpless.pipeline.intake import DEP_FILES
from bumpless.pipeline.scan import _tree, imports_package, python_files, usage_identifiers
from bumpless.radar.pypi import project_info
from bumpless.recipes import store
from bumpless.storage import db

REQ = re.compile(r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?P<spec>(?:[<>=!~]=?\s*[\w.*+!-]+\s*,?\s*)+)")
QUOTED = re.compile(r"""["']([^"'\n]+)["']""")


def dependencies(ws: Path) -> dict[str, str]:
    """{package: version spec} from requirements*.txt, pyproject.toml, setup.cfg and setup.py (pinned deps only)."""
    deps: dict[str, str] = {}
    for pattern in DEP_FILES:
        for f in sorted(ws.glob(pattern)):
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.lstrip().startswith("#"):
                    continue
                candidates = [line] if f.suffix in (".txt", ".cfg") else QUOTED.findall(line)
                for c in candidates:
                    m = REQ.match(c.split(";")[0])
                    if m:
                        deps.setdefault(m["name"].lower().replace("_", "-"), m["spec"].strip().rstrip(","))
    return deps


def current_version(spec: str) -> Version | None:
    """The version a spec pins or starts from (==, ~=, <=, >= in that order of preference)."""
    for op in ("==", "~=", "<=", ">="):
        m = re.search(rf"{re.escape(op)}\s*([\w.]+)", spec)
        if m:
            try:
                return Version(m.group(1).rstrip(".*"))
            except InvalidVersion:
                return None
    return None


def usage_count(ws: Path, package: str) -> tuple[int, int]:
    """(files importing the package, references to the names it imports)."""
    files, refs = 0, 0
    for f in python_files(ws):
        tree = _tree(f)
        if not tree or not imports_package(tree, package):
            continue
        files += 1
        mod = package.replace("-", "_")
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                names |= {(a.asname or a.name).split(".")[0] for a in n.names if a.name.split(".")[0] == mod}
            elif isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == mod:
                names |= {a.asname or a.name for a in n.names}
        refs += sum(isinstance(n, ast.Name) and n.id in names for n in ast.walk(tree))
    return files, refs


class Risk(BaseModel):
    risk: str  # low | medium | high
    reason: str


def cost_estimate(recipe_name: str | None) -> dict:
    """From stored real runs: reused-recipe average for this recipe, else the median first-run cost overall."""
    rows = db.query("SELECT recipe, reused, cost_usd FROM recipe_runs WHERE status != 'failed'")
    mine = [r["cost_usd"] for r in rows if r["recipe"] == recipe_name and r["reused"]]
    first = [r["cost_usd"] for r in rows if not r["reused"]]
    if mine:
        return {"usd": round(statistics.mean(mine), 4), "basis": f"average of {len(mine)} run(s) reusing this recipe"}
    if first:
        return {"usd": round(statistics.median(first), 4), "basis": f"median of {len(first)} first run(s), any package"}
    return {"usd": None, "basis": "no stored runs yet"}


async def assess(llm: LLM, package: str, frm: str, to: str, usage: list[str], recipe) -> Risk:
    rules = "\n".join(f"- {r.title}" for r in recipe.rules[:40]) if recipe else "(no recipe yet)"
    prompt = (f"Estimate the risk of migrating a Python codebase from `{package}` {frm} to {to}.\n"
              f"Names the codebase uses from it: {', '.join(usage[:40]) or '(none found)'}\n"
              f"Known breaking changes:\n{rules}\n"
              'Reply with JSON only: {"risk": "low|medium|high", "reason": "one short sentence"}')
    try:
        return await llm.chat("radar_risk", [{"role": "user", "content": prompt}], step="radar", schema=Risk,
                              max_tokens=3000)
    except LLMOutputError:
        return Risk(risk="unknown", reason="risk estimate unavailable")


async def radar(ws: Path, run_id: str = "radar") -> list[dict]:
    deps = dependencies(ws)
    infos = await asyncio.gather(*[project_info(p) for p in deps], return_exceptions=True)
    llm = LLM(run_id, "tiered", max_cost_usd=0.10)
    rows = []
    for (pkg, spec), info in zip(deps.items(), infos, strict=True):
        if isinstance(info, Exception):
            continue
        cur = current_version(spec)
        try:
            latest = Version(info["version"])
            allowed = latest in SpecifierSet(spec)
        except (InvalidVersion, InvalidSpecifier):
            continue
        if not cur or allowed or latest.major <= cur.major:
            continue
        files, refs = usage_count(ws, pkg)
        frm, to = str(cur.major), str(latest.major)
        recipe = store.load(pkg, frm, to)
        rows.append({
            "package": pkg, "spec": spec, "current": str(cur), "latest": str(latest),
            "majors_behind": latest.major - cur.major, "files": files, "references": refs,
            "recipe": {"version": recipe.recipe_version, "rules": len(recipe.rules),
                       "verified": sum(r.verified for r in recipe.rules)} if recipe else None,
            "target": f">={latest.major},<{latest.major + 1}",
            "_usage": usage_identifiers(ws, pkg), "_recipe": recipe,
        })
    risks = await asyncio.gather(*[assess(llm, r["package"], r["current"], r["latest"], r["_usage"], r["_recipe"])
                                   for r in rows])
    for r, risk in zip(rows, risks, strict=True):
        name = f"{r['package']}/{r['current'].split('.')[0]}-to-{r['latest'].split('.')[0]}" if r["recipe"] else None
        r |= {"risk": risk.risk, "risk_reason": risk.reason, "estimate": cost_estimate(name)}
        del r["_usage"], r["_recipe"]
    # value first: recipe available, then heavier usage
    rows.sort(key=lambda r: (r["recipe"] is None, -r["references"], -r["files"]))
    return rows

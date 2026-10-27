"""Migration recipes: verified rulebooks saved as JSON in recipes/<package>/<from>-to-<to>.json (the public
registry) plus a SQLite index of runs that used them."""

import time
from datetime import UTC, datetime
from pathlib import Path

from bumpless import fsutil
from bumpless.llm.schemas import Rule, Rulebook
from bumpless.settings import ROOT
from bumpless.storage import db

RECIPES_DIR = ROOT / "recipes"


def path_for(package: str, fm: str, tm: str, root: Path | None = None) -> Path:
    return (root or RECIPES_DIR) / package.lower() / f"{fm}-to-{tm}.json"


def load(package: str, fm: str, tm: str, root: Path | None = None) -> Rulebook | None:
    p = path_for(package, fm, tm, root)
    return Rulebook.model_validate_json(p.read_text(encoding="utf-8")) if p.exists() else None


def age_days(rb: Rulebook) -> float:
    if not rb.checked_at:
        return float("inf")
    return (datetime.now(UTC) - datetime.fromisoformat(rb.checked_at)).total_seconds() / 86400


def _key(r: Rule) -> tuple[str, str]:
    return (" ".join(r.old_pattern.split()).lower(), " ".join(r.new_pattern.split()).lower())


def merge(base: Rulebook, new_rules: list[Rule]) -> list[Rule]:
    """Append rules not already in the recipe (by old/new pattern). Returns the rules actually added."""
    seen = {_key(r) for r in base.rules}
    added = []
    for r in new_rules:
        if _key(r) not in seen:
            seen.add(_key(r))
            r.id = f"R{len(base.rules) + 1:03d}"
            base.rules.append(r)
            added.append(r)
    return added


def save(rb: Rulebook, run_id: str, root: Path | None = None) -> tuple[Rulebook, bool]:
    """Save the run's rulebook as a recipe, merging into an existing one. Returns (recipe, changed)."""
    existing = load(rb.package, rb.from_, rb.to, root)
    if existing is None:
        recipe, changed = rb.model_copy(deep=True), True
    else:
        recipe = existing
        learned = [r for r in rb.rules if r.learned_from_run == run_id]
        changed = bool(merge(recipe, [r.model_copy() for r in learned]))
        recipe.checked_at = max(recipe.checked_at, rb.checked_at)
        if changed:
            recipe.recipe_version += 1
    p = path_for(rb.package, rb.from_, rb.to, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    fsutil.write(p, recipe.model_dump_json(by_alias=True, indent=1) + "\n")
    return recipe, changed


def record_run(rb: Rulebook, run_id: str, reused: bool, status: str, cost_usd: float) -> None:
    db.insert("recipe_runs", {"recipe": f"{rb.package}/{rb.from_}-to-{rb.to}", "run_id": run_id, "ts": time.time(),
                              "reused": int(reused), "status": status, "cost_usd": cost_usd,
                              "recipe_version": rb.recipe_version})


def stats(root: Path | None = None) -> list[dict]:
    root = root or RECIPES_DIR
    out = []
    for p in sorted(root.glob("*/*.json")):
        rb = Rulebook.model_validate_json(p.read_text(encoding="utf-8"))
        key = f"{rb.package}/{rb.from_}-to-{rb.to}"
        runs = db.query("SELECT * FROM recipe_runs WHERE recipe=?", (key,))
        first = [r["cost_usd"] for r in runs if not r["reused"]]
        reuse = [r["cost_usd"] for r in runs if r["reused"]]
        out.append({
            "recipe": key, "package": rb.package, "from": rb.from_, "to": rb.to,
            "recipe_version": rb.recipe_version, "rules": len(rb.rules),
            "verified_rules": sum(r.verified for r in rb.rules), "checked_at": rb.checked_at,
            "runs": len(runs), "success_rate": (sum(r["status"] == "green" for r in runs) / len(runs)) if runs else None,
            "avg_first_run_cost": sum(first) / len(first) if first else None,
            "avg_reused_run_cost": sum(reuse) / len(reuse) if reuse else None,
            "path": p.relative_to(root.parent).as_posix() if root.parent in p.parents else str(p),
        })
    return out

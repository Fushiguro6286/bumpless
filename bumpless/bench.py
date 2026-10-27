"""Benchmark harness: run every repo in repos.yaml, store per-run summaries in SQLite + a JSON file."""

import asyncio
import json
import statistics
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

import git
import yaml

from bumpless import fsutil
from bumpless.pipeline.run import CHAR, run_migration
from bumpless.settings import settings
from bumpless.storage import db

RESULTS_DIR = Path("benchmarks/results")


def load(path: Path) -> list[dict]:
    """repos.yaml: a list of {name, kind: fixture|real, source, ref?, package, to}."""
    repos = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["repos"]
    for r in repos:
        missing = {"name", "source", "package", "to"} - set(r)
        if missing:
            raise ValueError(f"{r.get('name', r)}: missing {', '.join(sorted(missing))}")
        if r.get("kind", "fixture") == "real" and not r.get("ref"):
            raise ValueError(f"{r['name']}: real repos must pin a commit SHA in `ref`")
    return repos


def summarize(result: dict) -> dict:
    """The numbers the benchmark reports for one run, all taken from the run result."""
    t = result.get("tests") or {}
    after = t.get("after", {}).get("failing", [])
    ch = result.get("characterization") or {}
    obs = ch.get("observations") or 0
    char_after = [x for x in after if x.startswith(CHAR)]

    def repo_passed(run: dict | None, char_failing: int = 0) -> int:
        if not run:
            return 0
        if "repo_passed" in run:
            return run["repo_passed"]
        return run["passed"] - max(0, obs - char_failing)  # older results: subtract characterization passes

    # Repo tests broken by the bump = passed on the old version, not after the bump (a collection error breaks all).
    old = t.get("old", {}).get("passed", 0)
    red = repo_passed(t.get("new_before"), sum(x.startswith(CHAR) for x in t.get("new_before", {}).get("failing", [])))
    green = repo_passed(t.get("after"), len(char_after)) if "after" in t else red
    broken = max(0, old - red)
    cov = result.get("coverage") or {}
    err = result.get("error") or ""
    # An account/budget stop says nothing about the migration: don't count it as a failed migration.
    infra = any(s in err for s in ("402", "Payment Required", "Run budget of"))
    return {
        "status": "infra_error" if infra else result["status"], "error": result.get("error"),
        "old_version": result.get("old_version"), "new_version": result.get("new_version"),
        "tests_failing_before_fix": broken,
        "tests_fixed": max(0, min(broken, green - red)),
        "characterization_observations": obs,
        "characterization_pass_rate": round((obs - len(char_after)) / obs, 3) if obs and "after" in t else None,
        "coverage_percent": cov.get("percent") if cov.get("measured") else None,
        "duration_s": result.get("duration_s"),
        "cost_usd": round(result["cost"]["total_usd"], 6),
        "cost_by_tier": result["cost"]["by_tier"],
        "escalations": len(result.get("escalations") or []),
        "recipe_reused": bool(result.get("recipe_reused")),
        "manual_review": len(result.get("manual_review") or []),
    }


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 4) if xs else None


def aggregate(rows: list[dict]) -> dict:
    infra = sum(r["status"] == "infra_error" for r in rows)
    rows = [r for r in rows if r["status"] != "infra_error"]
    n = len(rows)
    by = {s: sum(r["status"] == s for r in rows) for s in ("green", "partial", "failed")} | {"infra_errors": infra}
    rates = [r["characterization_pass_rate"] for r in rows]
    return {
        "repos": n, **by, "success_rate": round(by["green"] / n, 3) if n else None,
        "tests_fixed": sum(r["tests_fixed"] for r in rows),
        "tests_failing_before_fix": sum(r["tests_failing_before_fix"] for r in rows),
        "median_characterization_pass_rate": _median(rates),
        "median_coverage_percent": _median([r["coverage_percent"] for r in rows]),
        "median_duration_s": _median([r["duration_s"] for r in rows]),
        "median_cost_usd": _median([r["cost_usd"] for r in rows]),
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
        "escalations": sum(r["escalations"] for r in rows),
    }


async def bench(path: Path, routing: str = "tiered", executor: str | None = None, concurrency: int = 2,
                only: list[str] | None = None) -> dict:
    repos = [r for r in load(path) if not only or r["name"] in only]
    bench_id = time.strftime("%Y%m%d-%H%M%S") + f"-{routing}"
    sem = asyncio.Semaphore(concurrency)

    async def one(r: dict) -> dict:
        async with sem:
            run_id = uuid.uuid4().hex[:10]
            result = await run_migration(r["source"], r["package"], r["to"], routing=routing, executor=executor,
                                         run_id=run_id, ref=r.get("ref"))
            row = {"name": r["name"], "kind": r.get("kind", "fixture"), "package": r["package"], "run_id": run_id,
                   **summarize(result)}
            db.insert("bench_runs", {"bench_id": bench_id, "ts": time.time(), "routing": routing, "name": r["name"],
                                     "kind": row["kind"], "run_id": run_id, "status": row["status"], "summary_json": row})
            return row

    rows = await asyncio.gather(*[one(r) for r in repos])
    out = {"bench_id": bench_id, "routing": routing, "created_at": time.time(), "commit": _commit(),
           "provider": urlparse(settings.nebius_base_url).hostname,
           "summary": aggregate(rows), "runs": rows}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    fsutil.write(RESULTS_DIR / f"{bench_id}.json", json.dumps(out, indent=2) + "\n")
    return out


def _commit() -> str | None:
    """The Bumpless commit a benchmark ran on ('+dirty' if there were uncommitted changes)."""
    try:
        repo = git.Repo(Path(__file__).resolve().parents[1])
        return repo.head.commit.hexsha[:7] + ("+dirty" if repo.is_dirty() else "")
    except (git.InvalidGitRepositoryError, ValueError):
        return None


def all_results() -> list[dict]:
    """Every stored benchmark file, newest first (the web Benchmark page and RESULTS.md read these)."""
    files = sorted(RESULTS_DIR.glob("*.json"), reverse=True) if RESULTS_DIR.exists() else []
    return [json.loads(f.read_text(encoding="utf-8")) for f in files]

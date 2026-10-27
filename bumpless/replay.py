"""Replays: real runs exported to demo/recordings/<run_id>.json so the demo works with no credits or keys."""

import json
import time

from bumpless import fsutil
from bumpless.pipeline.output import RUNS_DIR
from bumpless.settings import ROOT
from bumpless.storage import db

RECORDINGS_DIR = ROOT / "demo" / "recordings"


def public_result(result: dict | None) -> dict | None:
    """Drop local paths before anything leaves the machine."""
    if not result:
        return result
    result = dict(result)
    result.pop("workspace", None)
    src = result.get("source") or ""
    if src and "://" not in src:  # local path: keep only the folder name
        result["source"] = src.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    out = dict(result.get("output") or {})
    out.pop("patch", None)
    out.pop("report", None)
    result["output"] = out
    return result


def public_event(event: dict) -> dict:
    data = dict(event["data"])
    data.pop("traceback", None)  # never show raw stack traces
    for key in ("patch", "report", "workspace"):  # local file paths
        data.pop(key, None)
    return {"id": event["id"], "ts": event["ts"], "type": event["type"], "data": data}


def record(run_id: str, title: str = "") -> str:
    rows = db.query("SELECT * FROM runs WHERE id=?", (run_id,))
    if not rows or not rows[0]["result_json"]:
        raise ValueError(f"run {run_id} not found or not finished")
    r = rows[0]
    result = public_result(json.loads(r["result_json"]))
    evs = [public_event({"id": e["id"], "ts": e["ts"], "type": e["type"], "data": json.loads(e["data_json"])})
           for e in db.query("SELECT * FROM events WHERE run_id=? ORDER BY id", (run_id,))]
    files = {}
    for name in ("bumpless.patch", "report.md"):
        p = RUNS_DIR / run_id / name
        files[name] = p.read_text(encoding="utf-8") if p.exists() else None
    rec = {
        "id": run_id, "title": title or f"{r['package']} {result['old_version']} → {result['new_version']}",
        "recorded_at": time.time(),
        "run": {"id": r["id"], "status": r["status"], "package": r["package"], "target": r["target"],
                "routing": r["routing"], "created_at": r["created_at"], "result": result},
        "events": evs, "patch": files["bumpless.patch"], "report": files["report.md"],
    }
    path = RECORDINGS_DIR / f"{run_id}.json"
    fsutil.write(path, json.dumps(rec, ensure_ascii=False) + "\n")
    return str(path)


def load(rec_id: str) -> dict | None:
    if not rec_id.isalnum():
        return None
    p = RECORDINGS_DIR / f"{rec_id}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def list_recordings() -> list[dict]:
    out = []
    for p in sorted(RECORDINGS_DIR.glob("*.json")) if RECORDINGS_DIR.exists() else []:
        rec = json.loads(p.read_text(encoding="utf-8"))
        res = rec["run"]["result"] or {}
        out.append({"id": rec["id"], "title": rec["title"], "status": rec["run"]["status"],
                    "package": rec["run"]["package"], "created_at": rec["run"]["created_at"],
                    "cost_usd": (res.get("cost") or {}).get("total_usd"), "duration_s": res.get("duration_s"),
                    "coverage": (res.get("coverage") or {}).get("percent"),
                    "tests": (res.get("tests") or {}).get("after")})
    return out


def paced(events: list[dict], speed: float = 1.0):
    """(delay_seconds, event) pairs. speed 1 = the real recorded timing; faster speeds also cap long waits."""
    prev = None
    for ev in events:
        gap = 0.0 if prev is None else max(0.0, ev["ts"] - prev) / speed
        prev = ev["ts"]
        yield (gap if speed <= 1 else min(gap, 1.5)), ev

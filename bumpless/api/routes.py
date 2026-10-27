"""REST + SSE API for the web app."""

import asyncio
import json
import os
import time
import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from bumpless import events, replay
from bumpless.llm.router import MODES
from bumpless.pipeline.output import RUNS_DIR
from bumpless.recipes import store
from bumpless.settings import ROOT, settings
from bumpless.storage import db

router = APIRouter(prefix="/api")
FIXTURES_DIR = ROOT / "benchmarks" / "fixtures"
# Hosted demo: only bundled fixtures run live (never run untrusted code on our server).
ALLOW_ANY_REPO = os.environ.get("ALLOW_ANY_REPO", "") == "1"
_live = asyncio.Semaphore(1)
_tasks: set[asyncio.Task] = set()


def fixtures() -> list[dict]:
    out = []
    for d in sorted(FIXTURES_DIR.iterdir()):
        meta = d / "fixture.json"
        if meta.exists():
            out.append({"id": d.name, **json.loads(meta.read_text(encoding="utf-8"))})
    return out


@router.get("/fixtures")
def list_fixtures() -> list[dict]:
    return fixtures()


class RunRequest(BaseModel):
    fixture: str | None = None
    repo: str | None = None
    package: str
    target: str
    routing: str = "tiered"


def spent_today() -> float:
    """All LLM spend since 00:00 UTC (conservative: CLI runs on the same server count too)."""
    midnight = time.time() - time.time() % 86400
    return db.query("SELECT COALESCE(SUM(cost_usd), 0) AS s FROM llm_calls WHERE ts >= ?", (midnight,))[0]["s"]


def live_blocker() -> str | None:
    """Why live runs are unavailable right now (None = available). Replays always work."""
    if not settings.nebius_api_key or not settings.tavily_api_key:
        return "Live runs are not configured on this server (missing API keys)."
    if spent_today() >= settings.demo_daily_budget_usd:
        return "Today's live demo budget is used up. Live runs resume tomorrow (UTC)."
    if _live.locked():
        return "Another live run is in progress."
    return None


@router.post("/runs")
async def start_run(req: RunRequest, x_demo_password: str = Header("")) -> dict:
    from bumpless.pipeline.run import run_migration

    if settings.demo_password and x_demo_password != settings.demo_password:
        raise HTTPException(401, "This demo needs a password for live runs. Recorded runs are open to everyone.")
    if req.routing not in MODES:
        raise HTTPException(400, f"routing must be one of {MODES}")
    if req.fixture:
        if req.fixture not in {f["id"] for f in fixtures()}:
            raise HTTPException(404, "unknown fixture")
        source = str(FIXTURES_DIR / req.fixture)
    elif req.repo and ALLOW_ANY_REPO:
        source = req.repo
    else:
        raise HTTPException(403, "The hosted demo runs bundled fixtures only. Use the CLI or the GitHub Action for "
                                 "your own repositories.")
    if blocker := live_blocker():
        raise HTTPException(429 if _live.locked() else 503, f"{blocker} You can watch a recorded run instead.")
    run_id = uuid.uuid4().hex[:10]

    async def go():
        async with _live:
            await run_migration(source, req.package, req.target, routing=req.routing, run_id=run_id)

    task = asyncio.create_task(go())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    await asyncio.sleep(0.05)  # let the run register itself before the client subscribes
    return {"run_id": run_id}


@router.get("/runs")
def list_runs(limit: int = 50) -> list[dict]:
    rows = db.query("SELECT id, created_at, repo, package, target, routing, status FROM runs "
                    "ORDER BY created_at DESC LIMIT ?", (limit,))
    for r in rows:
        r["repo"] = r["repo"].replace("\\", "/").rsplit("/", 1)[-1] if r["repo"] else r["repo"]
    return rows


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    rows = db.query("SELECT * FROM runs WHERE id=?", (run_id,))
    if not rows:
        rec = replay.load(run_id)  # a recorded run works from a fresh clone (no database)
        if rec:
            return rec["run"] | {"recorded": True}
        raise HTTPException(404, "run not found")
    r = rows[0]
    result = replay.public_result(json.loads(r["result_json"])) if r["result_json"] else None
    return {"id": r["id"], "status": r["status"], "package": r["package"], "target": r["target"],
            "routing": r["routing"], "created_at": r["created_at"], "result": result}


def _artifact(run_id: str, name: str, key: str) -> str:
    p = RUNS_DIR / run_id / name
    if run_id.isalnum() and p.exists():
        return p.read_text(encoding="utf-8")
    rec = replay.load(run_id)
    if rec and rec.get(key):
        return rec[key]
    raise HTTPException(404, f"{key} not available")


@router.get("/runs/{run_id}/patch", response_class=PlainTextResponse)
def get_patch(run_id: str) -> str:
    return _artifact(run_id, "bumpless.patch", "patch")


@router.get("/runs/{run_id}/report", response_class=PlainTextResponse)
def get_report(run_id: str) -> str:
    return _artifact(run_id, "report.md", "report")


_public = replay.public_event


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request) -> StreamingResponse:
    if not db.query("SELECT id FROM runs WHERE id=?", (run_id,)) and replay.load(run_id):
        return await replay_events(run_id, request, speed=50.0)  # recorded run on a fresh clone: no live state
    queue: asyncio.Queue = asyncio.Queue()

    def listener(event: dict) -> None:
        if event["run_id"] == run_id:
            queue.put_nowait(event)

    events.add_listener(listener)  # subscribe before reading history so nothing is missed

    async def gen():
        try:
            last = 0
            for row in db.query("SELECT * FROM events WHERE run_id=? ORDER BY id", (run_id,)):
                ev = {"id": row["id"], "ts": row["ts"], "type": row["type"], "data": json.loads(row["data_json"])}
                last = ev["id"]
                yield f"data: {json.dumps(_public(ev))}\n\n"
                if ev["type"] == "run_finished":
                    return
            while not await request.is_disconnected():
                try:
                    ev = await asyncio.wait_for(queue.get(), 15)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if ev["id"] <= last:
                    continue
                yield f"data: {json.dumps(_public(ev))}\n\n"
                if ev["type"] == "run_finished":
                    return
        finally:
            events.remove_listener(listener)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/recipes")
def list_recipes() -> list[dict]:
    return store.stats()


@router.get("/bench")
def list_bench() -> list[dict]:
    """Stored benchmark results (benchmarks/results/*.json), newest first."""
    from bumpless.bench import all_results
    return all_results()


class RadarRequest(BaseModel):
    fixture: str | None = None
    repo: str | None = None


@router.post("/radar")
async def run_radar(req: RadarRequest) -> dict:
    """Read-only scan (files are parsed, never executed), so any repo is safe; cloning is limited like runs."""
    from bumpless.pipeline.intake import prepare_workspace
    from bumpless.radar.radar import radar

    if req.fixture:
        if req.fixture not in {f["id"] for f in fixtures()}:
            raise HTTPException(404, "unknown fixture")
        source = str(FIXTURES_DIR / req.fixture)
    elif req.repo and ALLOW_ANY_REPO:
        source = req.repo
    else:
        raise HTTPException(403, "The hosted demo scans bundled fixtures only; use `bumpless radar <repo>` locally.")
    ws = await asyncio.to_thread(prepare_workspace, source, "radar")
    return {"source": req.fixture or req.repo, "rows": await radar(ws)}


@router.get("/replays")
def list_replays() -> list[dict]:
    return replay.list_recordings()


@router.get("/replays/{rec_id}")
def get_replay(rec_id: str) -> dict:
    rec = replay.load(rec_id)
    if not rec:
        raise HTTPException(404, "recording not found")
    return rec["run"] | {"recorded": True, "recorded_at": rec["recorded_at"]}


@router.get("/replays/{rec_id}/events")
async def replay_events(rec_id: str, request: Request, speed: float = 1.0) -> StreamingResponse:
    rec = replay.load(rec_id)
    if not rec:
        raise HTTPException(404, "recording not found")

    async def gen():
        for delay, ev in replay.paced(rec["events"], max(1.0, min(speed, 50.0))):
            if await request.is_disconnected():
                return
            if delay:
                await asyncio.sleep(delay)
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


_status_cache: dict = {}


@router.get("/status")
async def status() -> dict:
    """What works right now. Cached for 60 s so the page can't burn API calls."""
    import httpx

    from bumpless.llm.client import check_models

    if _status_cache.get("at", 0) > time.time() - 60:
        return _status_cache["data"] | {"live": {"available": live_blocker() is None, "reason": live_blocker()}}
    models = {t: {"model": m, "ok": False} for t, m in settings.models.items()}
    tf_error = None
    try:
        for tier, ok in (await check_models()).items():
            models[tier]["ok"] = ok
    except Exception as e:  # message only: never a stack trace
        tf_error = str(e).splitlines()[0][:200] if str(e) else type(e).__name__
    tavily = {"ok": False, "error": None}
    if not settings.tavily_api_key:
        tavily["error"] = "TAVILY_API_KEY is not set"
    else:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get("https://api.tavily.com/usage", headers={"Authorization": f"Bearer {settings.tavily_api_key}"})
            tavily["ok"] = r.status_code == 200
            tavily["error"] = None if tavily["ok"] else f"HTTP {r.status_code}"
        except httpx.HTTPError as e:
            tavily["error"] = type(e).__name__
    last = db.query("SELECT id, created_at, package FROM runs WHERE status='green' ORDER BY created_at DESC LIMIT 1")
    data = {
        "token_factory": {"ok": tf_error is None and all(m["ok"] for m in models.values()), "error": tf_error,
                          "models": models},
        "tavily": tavily,
        "budget": {"daily_usd": settings.demo_daily_budget_usd, "spent_today_usd": round(spent_today(), 4),
                   "remaining_usd": round(max(0.0, settings.demo_daily_budget_usd - spent_today()), 4)},
        "last_successful_run": last[0] if last else None,
        "replays": len(replay.list_recordings()),
        "password_required": bool(settings.demo_password),
    }
    _status_cache.update(at=time.time(), data=data)
    return data | {"live": {"available": live_blocker() is None, "reason": live_blocker()}}

"""REST + SSE API for the web app."""

import asyncio
import json
import os
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from bumpless import events
from bumpless.llm.router import MODES
from bumpless.pipeline.output import RUNS_DIR
from bumpless.recipes import store
from bumpless.settings import ROOT
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


@router.post("/runs")
async def start_run(req: RunRequest) -> dict:
    from bumpless.pipeline.run import run_migration

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
    if _live.locked():
        raise HTTPException(429, "Another live run is in progress. Watch a recorded run, or try again in a few minutes.")
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
        raise HTTPException(404, "run not found")
    r = rows[0]
    result = json.loads(r["result_json"]) if r["result_json"] else None
    if result:
        result.pop("workspace", None)
        (result.get("output") or {}).pop("patch", None)
        (result.get("output") or {}).pop("report", None)
    return {"id": r["id"], "status": r["status"], "package": r["package"], "target": r["target"],
            "routing": r["routing"], "created_at": r["created_at"], "result": result}


@router.get("/runs/{run_id}/patch", response_class=PlainTextResponse)
def get_patch(run_id: str) -> str:
    p = RUNS_DIR / run_id / "bumpless.patch"
    if not run_id.isalnum() or not p.exists():
        raise HTTPException(404, "patch not available")
    return p.read_text(encoding="utf-8")


@router.get("/runs/{run_id}/report", response_class=PlainTextResponse)
def get_report(run_id: str) -> str:
    p = RUNS_DIR / run_id / "report.md"
    if not run_id.isalnum() or not p.exists():
        raise HTTPException(404, "report not available")
    return p.read_text(encoding="utf-8")


def _public(event: dict) -> dict:
    data = dict(event["data"])
    data.pop("traceback", None)  # never show raw stack traces in the UI
    return {"id": event["id"], "ts": event["ts"], "type": event["type"], "data": data}


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: str, request: Request) -> StreamingResponse:
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

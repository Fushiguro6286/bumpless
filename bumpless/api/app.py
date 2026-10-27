"""FastAPI app: the API plus the built React frontend (frontend/dist)."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bumpless.api.routes import router
from bumpless.settings import ROOT

DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="Bumpless", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(router)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{path:path}", include_in_schema=False)
def spa(path: str):
    """Serve the single-page app for every non-API route (client-side routing)."""
    target = (DIST / path).resolve()
    if path and target.is_file() and DIST.resolve() in target.parents:
        return FileResponse(target)
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Frontend not built. Run: cd frontend && npm install && npm run build"}

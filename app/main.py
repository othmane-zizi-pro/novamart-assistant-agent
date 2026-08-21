"""FastAPI application entry point.

Serves the JSON API and, when a frontend build exists, the static bundle. In
development the Vite dev server proxies /api here instead.
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import REPO_ROOT

FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="NovaMart Assistant")
    app.include_router(router)

    @app.get("/api/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}")
        async def spa(path: str) -> FileResponse:
            return FileResponse(FRONTEND_DIST / "index.html")

    return app


app = create_app()

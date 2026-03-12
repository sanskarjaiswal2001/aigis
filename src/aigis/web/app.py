"""FastAPI application factory for the Aigis web dashboard."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from aigis.config import AppConfig
from aigis.web.routes.actions import router as actions_router
from aigis.web.routes.audit import router as audit_router
from aigis.web.routes.events import router as events_router
from aigis.web.routes.runs import router as runs_router
from aigis.web.routes.scan import router as scan_router
from aigis.web.routes.settings import router as settings_router

_STATIC_DIR = Path(__file__).parent / "static"


def create_app(config: AppConfig, config_path: Path | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Aigis Dashboard",
        description="Web dashboard for the Aigis SRE monitoring agent",
        version="0.1.0",
    )

    # Store shared state
    app.state.config = config
    app.state.config_path = config_path or Path("config/default.yaml")

    # CORS: allow Vite dev server in development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes — all prefixed /api
    app.include_router(runs_router, prefix="/api", tags=["runs"])
    app.include_router(scan_router, prefix="/api", tags=["scan"])
    app.include_router(events_router, prefix="/api", tags=["events"])
    app.include_router(actions_router, prefix="/api", tags=["actions"])
    app.include_router(audit_router, prefix="/api", tags=["audit"])
    app.include_router(settings_router, prefix="/api", tags=["settings"])

    # Static SPA — must be mounted last so /api routes take priority
    _mount_static(app)

    return app


def _mount_static(app: FastAPI) -> None:
    """Mount the built React SPA. Skipped if static/ has no index.html (dev mode)."""
    index = _STATIC_DIR / "index.html"
    if not index.exists():
        return

    assets_dir = _STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        return FileResponse(str(index))

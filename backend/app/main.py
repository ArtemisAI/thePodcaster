"""ASGI entry-point for the FastAPI application.

This module
1. instantiates the :class:`fastapi.FastAPI` application;
2. wires all currently implemented API routers located in ``app.api``;
3. registers global exception handlers and middleware; and
4. performs a few start-up sanity checks (log directory, data locations
   writable, …).

The *upstream* branch referenced additional routers (``routes_video`` and
``routes_library``).  Those files are **not** present in the local code-base; if
we tried to import them the application would crash at start-up.  Until the
corresponding modules are added we purposefully omit these imports so that the
code runs successfully.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Internal utilities
from app.logging_config import LOG_DIR as APP_LOG_DIR
from app.logging_config import setup_logging
from app.utils.storage import (
    DATA_ROOT,
    OUTPUTS_DIR,
    PROCESSED_DIR,
    UPLOAD_DIR,
    ensure_dir_exists,
)

# API routers that are actually available in the repository
from app.api import (
    routes_audio,
    routes_llm,
    routes_outputs,
    routes_publish,
    routes_transcription,
)


# ---------------------------------------------------------------------------
# Logging must be configured as soon as possible so that any errors during
# import/start-up are captured.
# ---------------------------------------------------------------------------
setup_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


class AppBaseException(Exception):
    """Domain-level base exception so we can map to JSON responses easily."""

    def __init__(self, status_code: int, detail: str) -> None:  # noqa: D401
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def create_app() -> FastAPI:  # noqa: D401 – factory nomenclature is fine
    """Wire and return the FastAPI application instance."""

    app = FastAPI(
        title="The Podcaster API",
        version="0.1.0",
        docs_url="/api/docs",
    )

    # ------------------------------------------------------------------
    # Start-up checks – run synchronously because FastAPI will await them.
    # ------------------------------------------------------------------

    @app.on_event("startup")
    async def _startup_checks() -> None:  # noqa: D401
        logger.info("Running start-up checks …")

        for path in (APP_LOG_DIR, DATA_ROOT, UPLOAD_DIR, PROCESSED_DIR, OUTPUTS_DIR):
            try:
                ensure_dir_exists(Path(path))
            except Exception as exc:  # pragma: no cover – defensive
                logger.critical("Cannot create/access directory %s – %s", path, exc)
            else:
                writable = os.access(str(path), os.W_OK)
                logger.info("Directory %s is %swritable", path, "" if writable else "NOT ")

        logger.info("Start-up checks finished.")

    # ------------------------------------------------------------------
    # Exception handlers
    # ------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(  # noqa: D401
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:  # type: ignore[valid-type]
        logger.error("Request validation error: %s", exc.errors())
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(StarletteHTTPException)
    async def _http_error_handler(  # noqa: D401
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:  # type: ignore[valid-type]
        logger.error("HTTP exception %s: %s", exc.status_code, exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(AppBaseException)
    async def _app_error_handler(  # noqa: D401
        _request: Request,
        exc: AppBaseException,
    ) -> JSONResponse:  # type: ignore[valid-type]
        logger.error("Application exception: %s", exc.detail, exc_info=True)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def _generic_error_handler(  # noqa: D401
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:  # type: ignore[valid-type]
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers – *only* those that exist in the repo
    # ------------------------------------------------------------------

    app.include_router(routes_audio.router, prefix="/api/audio", tags=["audio"])
    app.include_router(routes_llm.router, prefix="/api/llm", tags=["llm"])
    app.include_router(routes_transcription.router, prefix="/api/transcription", tags=["transcription"])
    app.include_router(routes_publish.router, prefix="/api/publish", tags=["publish"])
    app.include_router(routes_outputs.router, prefix="/api/outputs", tags=["outputs"])

    # ------------------------------------------------------------------
    # Ensure DB schema exists (development convenience only).
    # ------------------------------------------------------------------

    try:
        from app.db.database import engine  # local import to avoid circular deps
        from app.db.base import Base

        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to create DB schema: %s", exc)

    # ------------------------------------------------------------------
    # Miscellaneous endpoints
    # ------------------------------------------------------------------

    @app.get("/api/health")
    async def _health() -> dict[str, str]:  # noqa: D401
        return {"status": "ok"}

    return app


# Instantiate at import time so `uvicorn app.main:app` works.
app: FastAPI = create_app()

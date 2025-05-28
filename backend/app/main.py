"""ASGI entry-point for the FastAPI application.

At a minimum, this file should:
* Instantiate `FastAPI`.
* Include routers from `app.api`.
* Provide a health-check route at `/api/health`.

Additional middleware (CORS, logging, tracing) will be added later.
"""

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

import logging

from .logging_config import setup_logging
from .api import routes_audio, routes_llm, routes_transcription, routes_publish
from fastapi.middleware.cors import CORSMiddleware # Ensure CORSMiddleware is imported if used

# Required imports for startup event
import os
from pathlib import Path
from app.utils.storage import DATA_ROOT, UPLOAD_DIR, PROCESSED_DIR, ensure_dir_exists

# Call logging setup at module level or early in create_app
setup_logging() 
# Alternatively, call inside create_app() if preferred for certain testing scenarios,
# but module level is fine for general use.

# --- Custom Base Exception (Optional) ---
class AppBaseException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)

def create_app() -> FastAPI:
    """Factory that wires and returns the FastAPI application."""
    
    # setup_logging() # Alternative placement for logging setup

    app = FastAPI(title="The Podcaster API", version="0.1.0", docs_url="/api/docs")

    # Get a logger instance for startup events
    logger_startup = logging.getLogger(__name__)

    # --- Startup Event Handler ---
    @app.on_event("startup")
    async def startup_event():
        logger_startup.info("Application startup: Performing initial checks...")
        
        # Log resolved paths
        logger_startup.info(f"Resolved DATA_ROOT: {DATA_ROOT.resolve()}")
        logger_startup.info(f"Resolved UPLOAD_DIR: {UPLOAD_DIR.resolve()}")
        logger_startup.info(f"Resolved PROCESSED_DIR: {PROCESSED_DIR.resolve()}")

        # Ensure UPLOAD_DIR exists
        try:
            ensure_dir_exists(UPLOAD_DIR) # ensure_dir_exists is not async
            logger_startup.info(f"Ensured UPLOAD_DIR exists at: {UPLOAD_DIR.resolve()}")
        except Exception as e:
            logger_startup.critical(f"Could not create UPLOAD_DIR at {UPLOAD_DIR.resolve()}: {e}", exc_info=True)
            # Potentially raise an exception here to halt startup if essential.

        # Check if UPLOAD_DIR is writable
        upload_dir_path_str = str(UPLOAD_DIR.resolve())
        if not os.access(upload_dir_path_str, os.W_OK):
            logger_startup.critical(f"CRITICAL: UPLOAD_DIR '{upload_dir_path_str}' is NOT WRITABLE by the application. File uploads will fail. Check host directory permissions if using Docker volume mounts.")
        else:
            logger_startup.info(f"UPLOAD_DIR '{upload_dir_path_str}' is writable.")
        
        logger_startup.info("Startup checks completed.")

    # --- Exception Handlers ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Log the validation error details
        logging.error(f"Request validation error: {exc.errors()}", exc_info=False) # exc_info=False as errors() is enough
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation Error", "errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException) # Handles FastAPI's HTTPException as it inherits from Starlette's
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logging.error(f"HTTP exception: {exc.status_code} - {exc.detail}", exc_info=False) # Usually no need for full stack trace
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    
    @app.exception_handler(AppBaseException) # Custom base exception
    async def app_base_exception_handler(request: Request, exc: AppBaseException):
        logging.error(f"Application exception: {exc.status_code} - {exc.detail}", exc_info=True)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(Exception) # Generic catch-all for 500 errors
    async def generic_exception_handler(request: Request, exc: Exception):
        # Log the full traceback for unexpected errors
        logging.error("Unhandled exception occurred", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    # --- Middleware ---
    # Add CORS middleware (ensure it's configured if it was there before)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
    # --- Routers ---
    # Include actual routers once they exist (e.g., audio_router)
    app.include_router(routes_audio.router, prefix="/api/audio", tags=["audio"])
    app.include_router(routes_llm.router, prefix="/api/llm", tags=["llm"])
    app.include_router(routes_transcription.router, prefix="/api/transcription", tags=["transcription"])
    app.include_router(routes_publish.router, prefix="/api/publish", tags=["publish"])

    # ------------------------------------------------------------------
    # Ensure database schema exists (development convenience).
    # ------------------------------------------------------------------
    try:
        from app.db.database import engine
        from app.db.base import Base

        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover – startup safeguard
        logging.getLogger(__name__).exception("Failed to create DB schema: %s", exc)


    @app.get("/api/health")
    async def health() -> dict[str, str]:
        logging.info("Health check endpoint was called.")
        return {"status": "ok"}

    return app


app = create_app()
# Add a logger instance for use in this file if needed outside of handlers/routes
# logger = logging.getLogger(__name__) # This was already here, the startup logger is local to create_app
logger.info("FastAPI application created and configured.")

"""ASGI entry-point for the FastAPI application.

At a minimum, this file should:
* Instantiate `FastAPI`.
* Include routers from `app.api`.
* Provide a health-check route at `/api/health`.

Additional middleware (CORS, logging, tracing) will be added later.
"""

# TODO: create FastAPI app and mount routers

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Factory that wires and returns the FastAPI application."""

    app = FastAPI(title="The Podcaster API", version="0.1.0", docs_url="/api/docs")

    # TODO: include actual routers once they exist (e.g., audio_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

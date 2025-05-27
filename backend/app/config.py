"""Application-wide configuration loader.

This module should:
1. Parse environment variables (DATABASE_URL, BROKER_URL, etc.).
2. Provide a singleton `Settings` object that other modules import.

Suggested implementation: use Pydantic's `BaseSettings` for type-safe
environment management.
"""

import os

class Settings:
    """Simple settings holder, values populated from environment variables."""
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "")
    OLLAMA_DEFAULT_MODEL: str = os.getenv("OLLAMA_DEFAULT_MODEL", "")
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "80"))

settings = Settings()

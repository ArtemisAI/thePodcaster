"""Application-wide configuration loader.

This module should:
1. Parse environment variables (DATABASE_URL, BROKER_URL, etc.).
2. Provide a singleton `Settings` object that other modules import.

Suggested implementation: use Pydantic's `BaseSettings` for type-safe
environment management.
"""

import os

class Settings:
    """Settings helper that gracefully falls back to sane defaults.

    Rationale
    ---------
    When docker-compose injects an environment variable whose value is empty
    (e.g. `DATABASE_URL=""`) ``os.getenv("DATABASE_URL", default)`` returns an
    empty string *not* ``None``.  That empty string then overrides the useful
    in-code default and downstream libraries (SQLAlchemy, Celery…) raise
    parsing errors just like the one seen in the worker logs:

        sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from string ''

    To avoid similar problems for every setting we use the idiom

        os.getenv(KEY) or DEFAULT

    so that *falsy* values ("", None, 0) are replaced by the specified
    DEFAULT.
    """

    DATABASE_URL: str = os.getenv('DATABASE_URL') or 'postgresql://podcaster:podcaster@db:5432/podcaster'
    CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL') or 'redis://broker:6379/0'
    CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND') or 'redis://broker:6379/0'
    OLLAMA_URL: str = os.getenv('OLLAMA_URL') or ''
    OLLAMA_DEFAULT_MODEL: str = os.getenv('OLLAMA_DEFAULT_MODEL') or ''
    FRONTEND_PORT: int = int(os.getenv('FRONTEND_PORT') or '80')

settings = Settings()

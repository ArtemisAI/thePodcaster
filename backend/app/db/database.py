"""Database engine & session utilities.

Use SQLAlchemy 2.0 style async engine or SQLModel convenience.
"""

# pylint: disable=import-error
# The DB helper is deliberately minimal: sync engine + classic session maker.

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.base import Base  # Global declarative base with all models registered

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

# Create SQLAlchemy engine
logger = logging.getLogger(__name__)
logger.info("Creating database engine for %s", settings.DATABASE_URL.split('@')[-1])
engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)

# Create a configured "SessionLocal" class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ---------------------------------------------------------------------------
# Schema creation – only in development / self-contained environments.
# In real deployments you would rely on migrations (Alembic), but creating the
# tables automatically keeps the developer experience smooth.
# ---------------------------------------------------------------------------

def _create_tables() -> None:  # pragma: no cover – rarely mocked in tests
    """Create all tables if they do not yet exist. Harmless when they do."""

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured")
    except Exception as exc:  # broad except OK in one-off helper
        logger.exception("Could not create DB tables: %s", exc)


# Import side-effect – letting the application decide when to create tables

def get_db():
    """Yields a database session and ensures it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("DB session closed")

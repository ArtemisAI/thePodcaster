"""Singleton declarative base and helper to initialise DB.

# Ensures all models are registered with Base when Base is imported.
# This is crucial for Base.metadata.create_all(engine) to see all tables.
from app import models # noqa - This line is important for model registration

The rest of the codebase can simply do

    from app.db.base import Base

to declare new ORM models.  Keeping the base in one place ensures that
`Base.metadata.create_all(bind=engine)` sees every mapped class.
"""

from sqlalchemy.orm import declarative_base

# The global declarative base instance used by every model
Base = declarative_base()

__all__ = ["Base"]

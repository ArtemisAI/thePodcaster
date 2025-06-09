# Ensure the `backend` package is importable as `app`
from __future__ import annotations

import sys
from pathlib import Path

# Add the backend directory to PYTHONPATH so imports like `from app.*` work
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Use an in-memory SQLite DB during tests unless overridden
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DB_ECHO", "0")

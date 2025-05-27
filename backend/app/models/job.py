"""SQLAlchemy model & helpers for processing jobs.

Only a subset of columns required by the current codebase is implemented.
Feel free to extend once additional metadata or relations are needed.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, Text

from app.db.base import Base


class JobStatus(str, Enum):
    """Enum representing the lifecycle of a background processing job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingJob(Base):
    """Persistent representation of a background processing job."""

    __tablename__ = "processing_jobs"

    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)
    job_type: str = Column(String(50), nullable=False)
    status: JobStatus = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    output_file_path: Optional[str] = Column(String(255), nullable=True)
    error_message: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Helper to convert enum to plain string for JSON responses
    @property
    def status_str(self) -> str:
        return self.status.value if isinstance(self.status, JobStatus) else str(self.status)


# The model is imported by Alembic / application start-up.  No run-time code here.

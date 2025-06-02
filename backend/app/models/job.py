"""SQLAlchemy model & helpers for processing jobs.

Only a subset of columns required by the current codebase is implemented.
Feel free to extend once additional metadata or relations are needed.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.transcript import Transcript # Assuming this is the correct path
from app.models.llm import LLMSuggestion # Assuming this is the correct path


class JobStatus(str, Enum):
    """Enum representing the lifecycle of a background processing job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobType(str, Enum):
    """Enum for different types of processing jobs."""
    AUDIO_CONCATENATION = "audio_concatenation" # Example existing type
    VIDEO_GENERATION = "video_generation"   # Example existing type
    TRANSCRIPTION = "transcription"
    LLM_SUGGESTION = "llm_suggestion"
    FILEBROWSER_AUDIO_UPLOAD = "filebrowser_audio_upload" # New type
    # Add other job types as needed


class ProcessingJob(Base):
    """Persistent representation of a background processing job."""

    __tablename__ = "processing_jobs"

    id: int = Column(Integer, primary_key=True, autoincrement=True, index=True)
    job_type: JobType = Column(SAEnum(JobType), nullable=False) # Changed to use JobType enum
    status: JobStatus = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    output_file_path: Optional[str] = Column(String(255), nullable=True)
    error_message: Optional[str] = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Fields for LLM suggestions
    generated_title: Optional[str] = Column(String(255), nullable=True)
    generated_summary: Optional[str] = Column(Text, nullable=True)

    # Relationships
    transcripts = relationship("Transcript", back_populates="job")
    llm_suggestions_collection = relationship("LLMSuggestion", back_populates="job")

    # Helper to convert enum to plain string for JSON responses
    @property
    def status_str(self) -> str: # type: ignore
        return self.status.value if isinstance(self.status, JobStatus) else str(self.status) # type: ignore

    @property
    def job_type_str(self) -> str: # type: ignore
        return self.job_type.value if isinstance(self.job_type, JobType) else str(self.job_type) # type: ignore


# The model is imported by Alembic / application start-up.  No run-time code here.

"""Pydantic / ORM models for transcripts."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.db.base import Base


class Transcript(Base):
    """
    Represents the transcription output for an audio processing job.

    Stores the plain text and SRT format transcriptions, the detected language,
    and a reference to the processing job that generated it.
    """
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="Primary key for the transcript record.")
    processing_job_id = Column(Integer, ForeignKey("processing_jobs.id"), nullable=False, index=True, comment="Foreign key linking to the 'processing_jobs' table.")
    text_content = Column(Text, nullable=True, comment="The full transcript in plain text format.")
    srt_content = Column(Text, nullable=True, comment="The transcript in SubRip (SRT) format, including timestamps.")
    language = Column(String(50), nullable=True, comment="The detected language of the audio (e.g., 'en', 'es').")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, comment="Timestamp of when the transcript record was created.")

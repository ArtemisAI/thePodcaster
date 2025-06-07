"""Pydantic models and SQLModel definitions for audio entities."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from app.db.base import Base


class AudioFile(Base):
    """
    Represents an uploaded audio file.

    Stores metadata about the audio file, including its original name,
    where it's saved, session ID for grouping uploads, size, content type,
    and upload timestamp.
    """
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, comment="Primary key for the audio file record.")
    original_filename = Column(String(255), comment="The original filename as uploaded by the user.")
    saved_path = Column(String(1024), nullable=False, comment="The path on the server where the file is stored, relative to a base data directory.")
    session_id = Column(String(36), index=True, nullable=False, comment="A unique session identifier (e.g., UUID) to group related audio files (intro, main, outro).")
    file_size = Column(Integer, nullable=False, comment="The size of the audio file in bytes.")
    content_type = Column(String(255), nullable=True, comment="The MIME type of the audio file (e.g., 'audio/mpeg').")
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, comment="Timestamp of when the file was uploaded.")


# TODO: create SQLModel class `ProcessingJob`

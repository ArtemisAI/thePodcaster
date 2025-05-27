"""Models for background processing jobs."""
from enum import Enum
from datetime import datetime

class JobStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ProcessingJob:
    """Represents a processing job with status and result metadata."""
    def __init__(
        self,
        id: int = None,
        job_type: str = None,
        status: JobStatus = None,
        output_file_path: str = None,
        error_message: str = None,
        created_at: datetime = None,
    ):
        self.id = id
        self.job_type = job_type
        self.status = status
        self.output_file_path = output_file_path
        self.error_message = error_message
        self.created_at = created_at or datetime.utcnow()
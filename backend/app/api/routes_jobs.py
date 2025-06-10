from __future__ import annotations

import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..db.database import SessionLocal
from ..models.job import ProcessingJob

router = APIRouter()
logger = logging.getLogger(__name__)


class JobInfo(BaseModel):
    id: int
    job_type: str
    status: str
    output_file_path: str | None = None
    error_message: str | None = None
    created_at: datetime


@router.get("", response_model=List[JobInfo])
async def list_jobs() -> List[JobInfo]:
    """Return all processing jobs."""
    db = SessionLocal()
    try:
        jobs = db.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).all()
        return [
            JobInfo(
                id=j.id,
                job_type=j.job_type,
                status=j.status_str,
                output_file_path=j.output_file_path,
                error_message=j.error_message,
                created_at=j.created_at,
            )
            for j in jobs
        ]
    except Exception as exc:
        logger.error("Failed to list jobs: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing jobs")
    finally:
        db.close()


@router.get("/{job_id}", response_model=JobInfo)
async def get_job(job_id: int) -> JobInfo:
    """Return a single processing job by ID."""
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        return JobInfo(
            id=job.id,
            job_type=job.job_type,
            status=job.status_str,
            output_file_path=job.output_file_path,
            error_message=job.error_message,
            created_at=job.created_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch job %s: %s", job_id, exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching job")
    finally:
        db.close()

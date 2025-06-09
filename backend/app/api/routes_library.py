from __future__ import annotations

import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..db.database import SessionLocal
from ..models.job import ProcessingJob, JobStatus
from ..utils.storage import DATA_ROOT

router = APIRouter()
logger = logging.getLogger(__name__)


class LibraryItem(BaseModel):
    job_id: int
    job_type: str
    output_file_path: str
    download_url: str


@router.get("", response_model=List[LibraryItem])
async def list_library_items() -> List[LibraryItem]:
    """List completed processing jobs with their download URLs."""
    db = SessionLocal()
    try:
        completed = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.status == JobStatus.COMPLETED)
            .all()
        )
        items: List[LibraryItem] = []
        for job in completed:
            if not job.output_file_path:
                continue
            rel_path = str(Path(job.output_file_path).relative_to(DATA_ROOT)) if Path(job.output_file_path).is_absolute() else job.output_file_path
            if job.job_type == "audio_processing":
                download_url = f"/api/audio/download/{job.id}"
            elif job.job_type == "video_generation":
                download_url = f"/api/video/download/{job.id}"
            else:
                download_url = f"/api/outputs/{Path(job.output_file_path).name}"
            items.append(
                LibraryItem(
                    job_id=job.id,
                    job_type=job.job_type,
                    output_file_path=rel_path,
                    download_url=download_url,
                )
            )
        return items
    except Exception as exc:
        logger.error("Failed to list library items: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing library items")
    finally:
        db.close()


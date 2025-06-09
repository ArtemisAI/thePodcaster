from __future__ import annotations

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from ..db.database import SessionLocal
from ..models.job import ProcessingJob, JobStatus
from ..utils.storage import DATA_ROOT, PROCESSED_DIR, ensure_dir_exists
from ..workers.tasks import generate_video_task

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/process/{audio_job_id}")
async def process_video(audio_job_id: int) -> dict:
    """Create a video generation job from a processed audio job."""
    db = SessionLocal()
    try:
        src_job = db.query(ProcessingJob).filter(ProcessingJob.id == audio_job_id).first()
        if not src_job or not src_job.output_file_path:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source job not found")

        new_job = ProcessingJob(job_type="video_generation", status=JobStatus.PENDING)
        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        output_filename = f"{new_job.id}_waveform.mp4"
        generate_video_task.delay(
            job_id=new_job.id,
            audio_input_path_str=src_job.output_file_path,
            output_filename=output_filename,
            resolution="1280x720",
            fg_color="white",
            bg_color="black",
            background_image_path_str=None,
        )
        return {"job_id": new_job.id, "message": "Video generation started."}
    finally:
        db.close()


@router.get("/download/{job_id}")
async def download_video(job_id: int) -> FileResponse:
    """Download the generated video for a completed job."""
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job not completed")
        file_path = PROCESSED_DIR / Path(job.output_file_path).name
        if not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return FileResponse(path=file_path, filename=file_path.name)
    finally:
        db.close()


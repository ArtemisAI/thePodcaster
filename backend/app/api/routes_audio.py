"""Audio-related REST endpoints.

Planned endpoints:

1. `POST /audio/upload` – Receive multipart/form-data with intro, main, outro.
2. `POST /audio/process` – Trigger audio normalization/concatenation.
3. `GET  /audio/{id}`      – Download processed audio file.
"""

# Audio-related REST endpoints.
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import uuid

from ..utils.storage import UPLOAD_DIR, PROCESSED_DIR, DATA_ROOT, ensure_dir_exists
from ..db.database import SessionLocal
from ..models.job import ProcessingJob, JobStatus
from ..workers.tasks import process_audio_task

router = APIRouter()

async def save_uploaded_file(file: UploadFile, session_id: str) -> Path:
    """Save an uploaded file under a session-specific directory."""
    session_dir = UPLOAD_DIR / session_id
    ensure_dir_exists(session_dir)
    file_path = session_dir / file.filename
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return file_path

@router.post("/upload")
async def upload_audio(
    main_track: UploadFile = File(...),
    intro: UploadFile | None = File(None),
    outro: UploadFile | None = File(None),
) -> dict:
    """Upload one or more audio tracks. Main track is required."""
    session_id = str(uuid.uuid4())
    saved = {}
    # Save main track
    main_path = await save_uploaded_file(main_track, session_id)
    saved["main_track"] = main_path
    # Optional tracks
    if intro:
        intro_path = await save_uploaded_file(intro, session_id)
        saved["intro"] = intro_path
    if outro:
        outro_path = await save_uploaded_file(outro, session_id)
        saved["outro"] = outro_path
    return {"upload_session_id": session_id, "saved_files": saved}

@router.post("/process/{session_id}")
async def process_audio(session_id: str) -> dict:
    """Trigger audio processing for uploaded tracks."""
    session_dir = UPLOAD_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    # Collect files in session directory
    input_files = [p for p in session_dir.glob("*") if p.is_file()]
    db = SessionLocal()
    job = ProcessingJob(job_type="audio_processing", status=JobStatus.PENDING)
    db.add(job)
    db.commit()
    db.refresh(job)
    # Prepare task arguments
    input_paths_str = [str(p.relative_to(DATA_ROOT)) for p in input_files]
    output_filename = f"{job.id}_processed.mp3"
    process_audio_task.delay(job_id=job.id, input_paths_str=input_paths_str, output_filename=output_filename)
    return {"job_id": job.id, "message": "Audio processing started."}

@router.get("/status/{job_id}")
async def get_job_status(job_id: int) -> dict:
    """Get the status of a processing job."""
    db = SessionLocal()
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    # Convert enum to its value if necessary
    status_value = job.status.value if hasattr(job.status, 'value') else job.status
    return {"job_id": job.id, "status": status_value, "output_file_path": job.output_file_path}

@router.get("/download/{job_id}")
async def download_processed_audio(job_id: int) -> FileResponse:
    """Download the processed audio file for a completed job."""
    db = SessionLocal()
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job not completed")
    # Build path to processed file
    file_name = Path(job.output_file_path).name
    file_path = PROCESSED_DIR / file_name
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processed file not found on server")
    return FileResponse(path=file_path, filename=file_name)

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
import logging # Added for logging

from ..utils.storage import UPLOAD_DIR, PROCESSED_DIR, DATA_ROOT, ensure_dir_exists
from ..db.database import SessionLocal
from ..models.job import ProcessingJob, JobStatus
from ..workers.tasks import process_audio_task

router = APIRouter()
logger = logging.getLogger(__name__) # Added logger instance

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

async def save_uploaded_file(file: UploadFile, session_id: str) -> Path:
    """Save an uploaded file under a session-specific directory."""
    session_dir = UPLOAD_DIR / session_id
    ensure_dir_exists(session_dir)
    logger.info(f"Ensured session directory exists at: {session_dir.resolve()}")
    file_path = session_dir / file.filename
    
    logger.info(f"Attempting to save file '{file.filename}' for session '{session_id}' to path '{file_path}'.")
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(8192)  # Read file in 8KB chunks
                if not chunk:
                    break
                f.write(chunk)
        logger.info(f"Successfully saved file '{file.filename}' for session '{session_id}' to path '{file_path}'.")
    except Exception as e:
        logger.error(f"Error during saving file '{file.filename}' for session '{session_id}' at path '{file_path}': {e}", exc_info=True)
        raise # Re-raise the exception to be caught by the caller
    return file_path

@router.post("/upload")
async def upload_audio(
    main_track: UploadFile = File(...),
    intro: UploadFile | None = File(None),
    outro: UploadFile | None = File(None),
) -> dict:
    """Upload one or more audio tracks. Main track is required."""
    logger.info("upload_audio endpoint called.")
    session_id = str(uuid.uuid4())
    saved = {}
    
    main_filename = main_track.filename if main_track else "N/A"
    intro_filename = intro.filename if intro else "None"
    outro_filename = outro.filename if outro else "None"
    logger.info(f"Received audio upload request for session '{session_id}'. Main: '{main_filename}', Intro: '{intro_filename}', Outro: '{outro_filename}'.")

    # Validate and save main track
    if main_track and main_track.filename:
        file_ext = Path(main_track.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            logger.error(f"Upload rejected for session '{session_id}': File '{main_track.filename}' has an unsupported extension. Allowed extensions: {ALLOWED_EXTENSIONS}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{main_track.filename}' has an unsupported extension. Allowed extensions are: {', '.join(ALLOWED_EXTENSIONS)}."
            )
    elif main_track and not main_track.filename: # Should not happen with FastAPI File(...) but good practice
        logger.warning(f"Upload rejected for session '{session_id}': main_track has no filename.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Main track file is invalid (no filename)."
        )
    # If main_track is None (not possible with File(...)) or filename is None after check, FastAPI would have already raised an error.
    # This explicit check is more for clarity if File(...) was optional.

    try:
        logger.info(f"Attempting to save main_track: '{main_track.filename}' for session '{session_id}'.")
        main_path = await save_uploaded_file(main_track, session_id)
        saved["main_track"] = str(main_path.relative_to(DATA_ROOT))
        logger.info(f"Successfully saved main_track: '{main_track.filename}' to '{saved['main_track']}' for session '{session_id}'.")
    except Exception as e:
        logger.error(f"Error saving file '{main_track.filename}' for session '{session_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving file: {main_track.filename}. Error: {str(e)}"
        )

    # Optional tracks
    if intro:
        if intro.filename:
            file_ext = Path(intro.filename).suffix.lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                logger.error(f"Upload rejected for session '{session_id}': File '{intro.filename}' has an unsupported extension. Allowed extensions: {ALLOWED_EXTENSIONS}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File '{intro.filename}' has an unsupported extension. Allowed extensions are: {', '.join(ALLOWED_EXTENSIONS)}."
                )
        else: # Optional file, but if provided, it must have a filename
            logger.warning(f"Upload rejected for session '{session_id}': intro file provided but has no filename.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Intro file is invalid (no filename)."
            )
        try:
            logger.info(f"Attempting to save intro: '{intro.filename}' for session '{session_id}'.")
            intro_path = await save_uploaded_file(intro, session_id)
            saved["intro"] = str(intro_path.relative_to(DATA_ROOT))
            logger.info(f"Successfully saved intro: '{intro.filename}' to '{saved['intro']}' for session '{session_id}'.")
        except Exception as e:
            logger.error(f"Error saving file '{intro.filename}' for session '{session_id}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file: {intro.filename}. Error: {str(e)}"
            )
            
    if outro:
        if outro.filename:
            file_ext = Path(outro.filename).suffix.lower()
            if file_ext not in ALLOWED_EXTENSIONS:
                logger.error(f"Upload rejected for session '{session_id}': File '{outro.filename}' has an unsupported extension. Allowed extensions: {ALLOWED_EXTENSIONS}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File '{outro.filename}' has an unsupported extension. Allowed extensions are: {', '.join(ALLOWED_EXTENSIONS)}."
                )
        else: # Optional file, but if provided, it must have a filename
            logger.warning(f"Upload rejected for session '{session_id}': outro file provided but has no filename.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outro file is invalid (no filename)."
            )
        try:
            logger.info(f"Attempting to save outro: '{outro.filename}' for session '{session_id}'.")
            outro_path = await save_uploaded_file(outro, session_id)
            saved["outro"] = str(outro_path.relative_to(DATA_ROOT))
            logger.info(f"Successfully saved outro: '{outro.filename}' to '{saved['outro']}' for session '{session_id}'.")
        except Exception as e:
            logger.error(f"Error saving file '{outro.filename}' for session '{session_id}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file: {outro.filename}. Error: {str(e)}"
            )
            
    logger.info(f"Completed audio upload processing for session '{session_id}'. Saved files: {list(saved.keys())}.")
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

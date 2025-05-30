"""Audio-related REST endpoints.

Planned endpoints:

1. `POST /audio/upload` – Receive multipart/form-data with intro, main, outro.
2. `POST /audio/process` – Trigger audio normalization/concatenation.
3. `GET  /audio/{id}`      – Download processed audio file.
"""

# Audio-related REST endpoints.
import os # Ensure os is imported
import shutil # Ensure shutil is imported
from typing import List # Ensure List is imported
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
import logging # Added for logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..utils.storage import UPLOAD_DIR, PROCESSED_DIR, DATA_ROOT, ensure_dir_exists
from ..db.database import SessionLocal
from ..models.job import ProcessingJob, JobStatus
from ..models.audio import AudioFile # Import AudioFile model
from ..workers.tasks import process_audio_task
from ..config import settings

router = APIRouter()
logger = logging.getLogger(__name__) # Added logger instance

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

async def save_uploaded_file(file: UploadFile, session_id: str, db: Session) -> Path:
    """Save an uploaded file under a session-specific directory and record it in the database."""
    session_dir = UPLOAD_DIR / session_id
    ensure_dir_exists(session_dir)
    logger.info(f"Ensured session directory exists at: {session_dir.resolve()}")
    file_path = session_dir / file.filename
    
    logger.info(f"Attempting to save file '{file.filename}' for session '{session_id}' to path '{file_path}'.")
    max_bytes = settings.max_upload_size_bytes
    bytes_written = 0
    try:
        with open(file_path, "wb") as f:
            while True:
                chunk = await file.read(8192)  # Read file in 8KB chunks
                if not chunk:
                    break
                bytes_written += len(chunk)
                # Enforce per-file size limit if configured (0 == unlimited)
                if max_bytes and bytes_written > max_bytes:
                    logger.warning(
                        "File upload exceeded max size. session=%s file=%s limit=%dMB",
                        session_id,
                        file.filename,
                        settings.MAX_UPLOAD_SIZE_MB,
                    )
                    # Remove partially written file before raising
                    try:
                        f.close()
                    except Exception:
                        pass
                    try:
                        file_path.unlink(missing_ok=True)
                    except Exception as cleanup_err:
                        logger.error(
                            "Failed to clean up over-sized temp file %s: %s",
                            file_path,
                            cleanup_err,
                        )

                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File '{file.filename}' exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB."
                    )
                f.write(chunk)
        logger.info(f"Successfully saved file '{file.filename}' for session '{session_id}' to path '{file_path}'.")

        # Create AudioFile record
        audio_file_record = AudioFile(
            original_filename=file.filename,
            saved_path=str(file_path.relative_to(DATA_ROOT)),
            session_id=session_id,
            file_size=file_path.stat().st_size,
            content_type=file.content_type,
            uploaded_at=datetime.utcnow()
        )
        db.add(audio_file_record)
        # db.commit() will be called in the main route
        logger.info(f"AudioFile record created for '{file.filename}' in session '{session_id}'.")

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
    
    db: Session = SessionLocal()
    try:
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
        elif main_track and not main_track.filename: 
            logger.warning(f"Upload rejected for session '{session_id}': main_track has no filename.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Main track file is invalid (no filename)."
            )

        try:
            logger.info(
                "Attempting to save main_track: '%s' for session '%s'. Size limit=%dMB",
                main_track.filename,
                session_id,
                settings.MAX_UPLOAD_SIZE_MB,
            )
            main_path = await save_uploaded_file(main_track, session_id, db)
            saved["main_track"] = str(main_path.relative_to(DATA_ROOT))
            logger.info(
                "Successfully saved main_track: '%s' (%s) to '%s' for session '%s'.",
                main_track.filename,
                main_track.content_type,
                saved["main_track"],
                session_id,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Unhandled exception while saving main track '%s' (session=%s): %s",
                main_track.filename,
                session_id,
                e,
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file: {main_track.filename}. Error: {str(e)}",
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
            else: 
                logger.warning(f"Upload rejected for session '{session_id}': intro file provided but has no filename.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Intro file is invalid (no filename)."
                )
            try:
                logger.info(f"Attempting to save intro: '{intro.filename}' for session '{session_id}'.")
                intro_path = await save_uploaded_file(intro, session_id, db)
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
            else: 
                logger.warning(f"Upload rejected for session '{session_id}': outro file provided but has no filename.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Outro file is invalid (no filename)."
                )
            try:
                logger.info(f"Attempting to save outro: '{outro.filename}' for session '{session_id}'.")
                outro_path = await save_uploaded_file(outro, session_id, db)
                saved["outro"] = str(outro_path.relative_to(DATA_ROOT))
                logger.info(f"Successfully saved outro: '{outro.filename}' to '{saved['outro']}' for session '{session_id}'.")
            except Exception as e:
                logger.error(f"Error saving file '{outro.filename}' for session '{session_id}': {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error saving file: {outro.filename}. Error: {str(e)}"
                )
        
        db.commit() # Commit all AudioFile records for this session
        logger.info(f"Successfully committed AudioFile records for session '{session_id}'.")
        logger.info(f"Completed audio upload processing for session '{session_id}'. Saved files: {list(saved.keys())}.")
        return {"upload_session_id": session_id, "saved_files": saved}
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e: # Catch other exceptions, including potential DB errors during commit
        logger.error(f"An unexpected error occurred in upload_audio for session '{session_id}': {e}", exc_info=True)
        # db.rollback() # Not strictly necessary with SessionLocal if commit failed, but good practice
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during processing: {str(e)}"
        )
    finally:
        db.close()
        logger.info(f"Database session closed for session_id '{session_id}'.")

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

@router.get("/uploads", response_model=List[str])
async def list_upload_sessions():
    logger.info("Listing all upload sessions.")
    if not UPLOAD_DIR.exists() or not UPLOAD_DIR.is_dir():
        logger.error(f"UPLOAD_DIR {UPLOAD_DIR} does not exist or is not a directory.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Upload directory not configured or found.")
    try:
        session_ids = [entry.name for entry in UPLOAD_DIR.iterdir() if entry.is_dir()]
        logger.info(f"Found sessions: {session_ids}")
        return session_ids
    except Exception as e:
        logger.error(f"Error listing upload sessions: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing upload sessions.")

@router.get("/uploads/{session_id}", response_model=List[str])
async def list_files_in_session(session_id: str):
    logger.info(f"Listing files for session_id: {session_id}")
    session_path = UPLOAD_DIR / session_id
    if not session_path.exists() or not session_path.is_dir():
        logger.warning(f"Session directory {session_path} not found for session_id: {session_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found.")
    try:
        files = [entry.name for entry in session_path.iterdir() if entry.is_file()]
        logger.info(f"Files in session {session_id}: {files}")
        return files
    except Exception as e:
        logger.error(f"Error listing files for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing files in session.")

from pydantic import BaseModel # For response model

class ProcessedFileDetail(BaseModel):
    job_id: int
    output_file_path: str
    # Add other fields from ProcessingJob if needed, e.g., created_at

@router.get("/processed_files", response_model=List[ProcessedFileDetail])
async def list_processed_files():
    logger.info("Listing all processed files.")
    db = SessionLocal()
    try:
        # Assuming JobStatus.COMPLETED is the correct enum member for completed jobs
        completed_jobs = db.query(ProcessingJob).filter(ProcessingJob.status == JobStatus.COMPLETED).all()
        processed_files = [
            ProcessedFileDetail(job_id=job.id, output_file_path=str(Path(job.output_file_path).relative_to(DATA_ROOT)) if job.output_file_path else "N/A")
            for job in completed_jobs if job.output_file_path # Ensure output_file_path exists
        ]
        logger.info(f"Found {len(processed_files)} processed files.")
        return processed_files
    except Exception as e:
        logger.error(f"Error listing processed files: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing processed files.")
    finally:
        db.close()

@router.get("/uploads/{session_id}/{filename}")
async def get_uploaded_file(session_id: str, filename: str):
    logger.info(f"Attempting to serve file '{filename}' from session '{session_id}'.")
    
    # Basic security check for filename to prevent directory traversal
    # Though Path operations usually handle this well, an explicit check adds safety.
    if ".." in filename or "/" in filename: # Disallow path traversal components
        logger.warning(f"Potentially malicious filename '{filename}' requested in session '{session_id}'.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    file_path = UPLOAD_DIR / session_id / filename
    
    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"File '{filename}' not found in session '{session_id}' at path '{file_path}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    
    try:
        # Determine media type based on extension for common audio types
        media_type_map = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4", # m4a is often mp4 container
            ".aac": "audio/aac",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
        }
        file_ext = Path(filename).suffix.lower()
        media_type = media_type_map.get(file_ext, "application/octet-stream") # Default if unknown
        
        logger.info(f"Serving file '{file_path}' with media type '{media_type}'.")
        return FileResponse(path=file_path, media_type=media_type, filename=filename)
    except Exception as e:
        logger.error(f"Error serving file '{filename}' from session '{session_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error serving file.")

@router.delete("/uploads/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload_session(session_id: str):
    logger.info(f"Attempting to delete upload session: {session_id}")
    session_path = UPLOAD_DIR / session_id
    if not session_path.exists() or not session_path.is_dir():
        logger.warning(f"Upload session directory {session_path} not found for deletion.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found.")
    try:
        shutil.rmtree(session_path)
        logger.info(f"Successfully deleted upload session directory: {session_path}")
        # No content to return, so FastAPI will handle the 204 response.
    except Exception as e:
        logger.error(f"Error deleting upload session {session_id} at {session_path}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting upload session.")

@router.delete("/processed_files/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_processed_file(job_id: int):
    logger.info(f"Attempting to delete processed file for job_id: {job_id}")
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            logger.warning(f"Job with id {job_id} not found for processed file deletion.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

        if not job.output_file_path:
            logger.info(f"Job {job_id} has no output file path specified. Nothing to delete.")
            # This could also be a 404 if the expectation is that a file should exist
            # For now, treating as "nothing to do", so 204 is acceptable.
            return 

        # Assuming job.output_file_path is just the filename, e.g., "job_id_processed.mp3"
        # as suggested by `output_filename = f"{job.id}_processed.mp3"` in process_audio endpoint
        file_name = Path(job.output_file_path).name # Get just the filename part
        file_path = PROCESSED_DIR / file_name
        
        logger.info(f"Target file path for deletion: {file_path} (from job {job_id}, output_path: {job.output_file_path})")

        if not file_path.exists() or not file_path.is_file():
            logger.warning(f"Processed file {file_path} not found on disk for job {job_id}.")
            # Optionally update DB even if file is missing, to reflect it's gone
            job.output_file_path = None # Or an empty string
            db.commit()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processed file not found on disk.")

        os.remove(file_path)
        logger.info(f"Successfully deleted processed file: {file_path} for job {job_id}.")
        
        # Update database to reflect deletion
        job.output_file_path = None # Or some other indicator
        # job.status = JobStatus.ARCHIVED or similar if you add such a status
        db.commit()
        
        # No content to return
    except HTTPException: # Re-raise HTTPExceptions
        raise
    except Exception as e:
        db.rollback() # Rollback on other errors
        logger.error(f"Error deleting processed file for job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting processed file.")
    finally:
        db.close()

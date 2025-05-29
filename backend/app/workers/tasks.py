"""Celery task definitions."""

from celery import Celery, Task # Import Task for custom base class
from celery.signals import setup_logging as setup_celery_logging # To potentially customize Celery's own logging
from pathlib import Path
import logging # Python's standard logging
import os
import ffmpeg # For ffmpeg.Error in error handling

# Import settings and services
from app.config import settings
from app.db.database import SessionLocal
from ..models.audio import AudioFile # Import AudioFile model
from ..models.job import ProcessingJob, JobStatus
from ..models.transcript import Transcript # Import Transcript model
from ..services.audio_processing import merge_and_normalize_audio
from ..services.transcription import transcribe_audio
from ..utils.storage import (
    UPLOAD_DIR, PROCESSED_DIR, TRANSCRIPT_DIR,
    ensure_dir_exists, DATA_ROOT, save_transcript_to_files
)
from ..logging_config import setup_logging as setup_app_logging

# Ensure DB schema exists when the worker process starts.  This way we do not
# depend on the FastAPI container running first (handy during local dev)
from app.db.base import Base
from app.db.database import engine

# Creating tables is a no-op if they already exist (and very fast).
Base.metadata.create_all(bind=engine)

# --- Logger Setup ---
# Ensure app-level logging is configured when a worker starts.
# This will apply the formatters and handlers defined in logging_config.py.
setup_app_logging()
logger = logging.getLogger(__name__) # Logger for this module (tasks.py)


# --- Celery Application Setup ---
# Using settings from backend.app.config
celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.workers.tasks'] # Ensures tasks are discoverable
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Consider adding:
    # task_track_started=True, # To report 'started' state
    # worker_send_task_events=True, # For monitoring tools like Flower
)

# Optional: Customize Celery's own logging setup
# @setup_celery_logging.connect
# def on_celery_setup_logging(**kwargs):
#     # This function is called when Celery sets up its loggers.
#     # You can integrate it further with your app's logging here if needed,
#     # but usually, configuring the root logger via setup_app_logging() is sufficient.
#     # For example, you could remove Celery's default handlers and rely on yours.
#     pass
# logger.info(f"Celery app configured with broker: {settings.CELERY_BROKER_URL}")


# --- Base Task with Error Handling & DB Session (Optional but good practice) ---
class BaseTaskWithDB(Task):
    """Base Celery Task with automatic DB session management and logging."""
    abstract = True # Means this class won't be registered as a task itself

    def __call__(self, *args, **kwargs):
        logger.info(f"Task {self.name} [{self.request.id}] called with args: {args}, kwargs: {kwargs}")
        return super().__call__(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {self.name} [{task_id}] failed: {exc}", exc_info=einfo)
        # Here you could add more robust error reporting, e.g., to an external service
        # Update job status to FAILED in DB if job_id is available
        job_id = kwargs.get('job_id') or (args[0] if args and isinstance(args[0], int) else None)
        if job_id:
            db = SessionLocal()
            try:
                job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                if job:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Task failed: {str(exc)[:500]}" # Truncate error message
                    db.commit()
                else:
                    logger.warning(f"Job with id {job_id} not found for failure update of task {self.name} [{task_id}].")
            except Exception as db_exc:
                logger.error(f"DB error during task failure handling for job {job_id}, task {self.name} [{task_id}]: {db_exc}", exc_info=True)
                db.rollback()
            finally:
                db.close()
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {self.name} [{task_id}] completed successfully. Result: {retval}")
        super().on_success(retval, task_id, args, kwargs)


# --- Audio Processing Task ---
@celery_app.task(name="process_audio_task", base=BaseTaskWithDB)
def process_audio_task(job_id: int, input_paths_str: list[str], output_filename: str):
    logger.info(f"Starting audio processing for job_id: {job_id}. Inputs: {input_paths_str}, Output: {output_filename}")
    db = SessionLocal()
    job = None
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in DB for audio processing.")
            raise ValueError(f"Job {job_id} not found.") # Will be caught by BaseTask's on_failure

        job.status = JobStatus.PROCESSING
        db.commit()
        logger.debug(f"Job {job_id} status updated to PROCESSING.")

        input_file_paths = [DATA_ROOT / Path(p_str) for p_str in input_paths_str]
        ensure_dir_exists(PROCESSED_DIR)
        output_path = PROCESSED_DIR / output_filename
        
        logger.debug(f"Full input paths for job {job_id}: {input_file_paths}")
        logger.debug(f"Full output path for job {job_id}: {output_path}")

        processed_file_path = merge_and_normalize_audio(input_files=input_file_paths, output_path=output_path)

        job.status = JobStatus.COMPLETED
        job.output_file_path = str(processed_file_path.relative_to(DATA_ROOT))
        job.error_message = None # Clear any previous errors
        logger.info(f"Audio processing successful for job_id: {job_id}. Output: {job.output_file_path}")
        return {"job_id": job_id, "output_path": job.output_file_path, "status": "COMPLETED"}

    except FileNotFoundError as e:
        logger.error(f"File not found during audio processing for job {job_id}: {e}", exc_info=True)
        if job: job.error_message = f"File not found: {e}"
        raise # Re-raise to be handled by BaseTaskWithDB.on_failure or Celery
    except ffmpeg.Error as e:
        err_detail = e.stderr.decode('utf8') if e.stderr else str(e)
        logger.error(f"FFmpeg error during audio processing for job {job_id}: {err_detail}", exc_info=True)
        if job: job.error_message = f"FFmpeg error: {err_detail[:500]}"
        raise
    except Exception as e:
        logger.error(f"Unexpected error during audio processing for job {job_id}: {e}", exc_info=True)
        if job: job.error_message = f"Unexpected error: {str(e)[:500]}"
        raise
    finally:
        if job: # Commit any changes like error messages if not already committed by success
            db.commit()
        db.close()


# --- Video Generation Task ---
@celery_app.task(name="generate_video_task", base=BaseTaskWithDB)
def generate_video_task(
    job_id: int, audio_input_path_str: str, output_filename: str, 
    resolution: str, fg_color: str, bg_color: str, 
    background_image_path_str: str | None = None
):
    logger.info(f"Starting video generation for job_id: {job_id}. Audio: {audio_input_path_str}, Output: {output_filename}")
    db = SessionLocal()
    job = None
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for video generation.")
            raise ValueError(f"Job {job_id} not found.")

        job.status = JobStatus.PROCESSING
        db.commit()

        audio_input_path = DATA_ROOT / Path(audio_input_path_str)
        video_output_path = PROCESSED_DIR / output_filename
        background_image_path = DATA_ROOT / Path(background_image_path_str) if background_image_path_str else None
        
        ensure_dir_exists(PROCESSED_DIR)
        logger.debug(f"Video generation params for job {job_id} - audio: {audio_input_path}, video_out: {video_output_path}, bg_img: {background_image_path}")

        generated_video_path = generate_waveform_video(
            audio_input_path, video_output_path, resolution, fg_color, bg_color, background_image_path
        )

        job.status = JobStatus.COMPLETED
        job.output_file_path = str(generated_video_path.relative_to(DATA_ROOT))
        job.error_message = None
        logger.info(f"Video generation successful for job_id: {job_id}. Output: {job.output_file_path}")
        return {"job_id": job_id, "output_path": job.output_file_path, "status": "COMPLETED"}

    except FileNotFoundError as e:
        logger.error(f"File not found during video generation for job {job_id}: {e}", exc_info=True)
        if job: job.error_message = f"File not found: {e}"
        raise
    except ffmpeg.Error as e:
        err_detail = e.stderr.decode('utf8') if e.stderr else str(e)
        logger.error(f"FFmpeg error during video generation for job {job_id}: {err_detail}", exc_info=True)
        if job: job.error_message = f"FFmpeg error: {err_detail[:500]}"
        raise
    except Exception as e:
        logger.error(f"Unexpected error during video generation for job {job_id}: {e}", exc_info=True)
        if job: job.error_message = f"Unexpected error: {str(e)[:500]}"
        raise
    finally:
        if job: db.commit()
        db.close()


# --- Transcription Task ---
@celery_app.task(name="transcribe_audio_task", base=BaseTaskWithDB)
def transcribe_audio_task(job_id: int, audio_input_path_str: str, output_basename: str):
    logger.info(f"Starting transcription for job_id: {job_id}. Audio: {audio_input_path_str}, Basename: {output_basename}")
    db = SessionLocal()
    job = None
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for transcription.")
            raise ValueError(f"Job {job_id} not found.")

        job.status = JobStatus.PROCESSING
        db.commit()

        audio_input_path = DATA_ROOT / Path(audio_input_path_str)
        logger.debug(f"Transcription input path for job {job_id}: {audio_input_path}")

        plain_text, srt_text, language = transcribe_audio(audio_input_path)
        
        ensure_dir_exists(TRANSCRIPT_DIR) # Ensure transcript dir exists
        txt_rel_path, srt_rel_path = save_transcript_to_files(
            output_basename, plain_text, srt_text, TRANSCRIPT_DIR
        )

        # Create and save Transcript record
        transcript_record = Transcript(
            processing_job_id=job.id,
            text_content=plain_text,
            srt_content=srt_text,
            language=language 
            # created_at will use the model's default
        )
        db.add(transcript_record)
        # The commit will happen in the finally block

        job.status = JobStatus.COMPLETED
        job.output_file_path = str(srt_rel_path) # Store SRT path as the main output
        job.error_message = None
        # Consider storing txt_rel_path in a new field or a JSON structure in job.results if needed.
        logger.info(f"Transcription successful for job_id: {job_id}. SRT: {srt_rel_path}, TXT: {txt_rel_path}")
        logger.info(f"Transcript for job_id: {job_id} (language: {language}) saved to database.")
        return {"job_id": job_id, "srt_path": str(srt_rel_path), "txt_path": str(txt_rel_path), "status": "COMPLETED", "language": language}

    except FileNotFoundError as e:
        logger.error(f"File not found during transcription for job {job_id}: {e}", exc_info=True)
        if job: job.error_message = f"File not found: {e}"
        raise
    except RuntimeError as e: # transcribe_audio can raise RuntimeError for model issues
        logger.error(f"Transcription runtime error for job {job_id}: {e}", exc_info=True)
        if job: job.error_message = f"Transcription runtime error: {str(e)[:500]}"
        raise
    except Exception as e:
        logger.error(f"Unexpected error during transcription for job {job_id}: {e}", exc_info=True)
        if job: job.error_message = f"Unexpected error: {str(e)[:500]}"
        raise
    finally:
        if job: db.commit()
        db.close()

logger.info("Celery tasks defined and logging configured.")

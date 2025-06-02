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
from ..models.job import ProcessingJob, JobStatus, JobType # Added JobType
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
# Base.metadata.create_all(bind=engine) # Temporarily commented out for testing to avoid DB connection on import

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

# --- File Browser Hook Task ---
import asyncio
import shutil # For file copy, though merge_and_normalize_audio might handle it.
# Import generate_suggestions from app.services.llm
from ..services.llm import generate_suggestions as generate_suggestions_service # Renamed to avoid conflict

@celery_app.task(name="handle_filebrowser_upload_task", base=BaseTaskWithDB)
def handle_filebrowser_upload(file_path_str: str, username: str = None, job_id_override: int = None): # Added job_id_override for BaseTaskWithDB
    """
    Celery task to process a single audio file uploaded via File Browser.
    This task creates a ProcessingJob, normalizes the audio, transcribes it,
    and generates LLM suggestions.
    """
    # Note: BaseTaskWithDB expects job_id for its on_failure.
    # Since this task creates the job, we'll manage job status updates internally primarily.
    # If job_id_override is passed (e.g. if API creates job first), it could be used.

    logger.info(f"Celery Task: Processing file {file_path_str} from user {username}.")
    db = SessionLocal()
    db_job = None # Initialize db_job to None

    try:
        original_file_path = Path(file_path_str)
        original_filename = original_file_path.name
        original_filename_stem = original_file_path.stem

        # 1. Create ProcessingJob entry in DB
        # If job_id_override is provided, we might fetch an existing job.
        # For now, assume this task always creates a new job.
        if job_id_override:
             db_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id_override).first()
             if not db_job:
                 logger.error(f"Job with override ID {job_id_override} not found. Cannot proceed.")
                 # This is an issue, BaseTaskWithDB might not handle this if job_id is passed but invalid.
                 raise ValueError(f"Job with override ID {job_id_override} not found.")
        else:
            db_job = ProcessingJob(
                job_type=JobType.FILEBROWSER_AUDIO_UPLOAD, # Use JobType enum
                status=JobStatus.PENDING
                # Add other relevant fields if the model is extended, e.g., original_filename, user_info
            )
            db.add(db_job)
            db.commit()
            db.refresh(db_job)

        current_job_id = db_job.id # Use this for logging and path creation
        logger.info(f"Created/Using job {current_job_id} for file {original_filename}")

        db_job.status = JobStatus.PROCESSING
        db.commit()

        # Define paths
        job_processed_dir = PROCESSED_DIR / str(current_job_id)
        ensure_dir_exists(job_processed_dir)

        # Output of merge_and_normalize_audio will be MP3
        normalized_audio_filename = f"normalized_{original_filename_stem}.mp3"
        normalized_audio_path = job_processed_dir / normalized_audio_filename

        logger.info(f"Job {current_job_id}: Starting audio normalization for {original_file_path} to {normalized_audio_path}")
        actual_normalized_path_obj = merge_and_normalize_audio(
            input_files=[original_file_path],
            output_path=normalized_audio_path
        )
        db_job.output_file_path = str(actual_normalized_path_obj.relative_to(DATA_ROOT))
        db.commit()
        logger.info(f"Job {current_job_id}: Audio normalization complete. Output: {db_job.output_file_path}")

        # 3. Transcribe Audio
        logger.info(f"Job {current_job_id}: Starting transcription for {actual_normalized_path_obj}")
        plain_text, srt_text, language = transcribe_audio(audio_input_path=actual_normalized_path_obj)

        if plain_text is not None and srt_text is not None:
            transcript_basename = f"job_{current_job_id}_{original_filename_stem}"
            # Save transcript files to the global TRANSCRIPT_DIR
            txt_rel_path, srt_rel_path = save_transcript_to_files(
                output_basename=transcript_basename,
                plain_text=plain_text,
                srt_text=srt_text,
                transcript_dir=TRANSCRIPT_DIR # Use global transcript dir
            )

            # Create Transcript DB record
            transcript_record = Transcript(
                processing_job_id=current_job_id,
                text_content=plain_text,
                srt_content=srt_text,
                language=language
            )
            db.add(transcript_record)
            # Update job's main output to be the SRT from transcription, similar to transcribe_audio_task
            # This overwrites the normalized audio path, consider if both are needed or how to store multiple outputs.
            # For now, let's assume the SRT is a primary output.
            # db_job.output_file_path = str(srt_rel_path) # Optional: if SRT is considered main output over audio
            db.commit()
            logger.info(f"Job {current_job_id}: Transcription complete. Saved to files and DB. Language: {language}")
        else:
            logger.warning(f"Job {current_job_id}: Transcription returned empty results.")
            # Potentially set status to something like PARTIAL_SUCCESS or log as warning

        # 4. Generate LLM Suggestions (if transcript text exists)
        if plain_text:
            logger.info(f"Job {current_job_id}: Generating LLM suggestions.")
            try:
                # Running async function from sync Celery task
                suggestions = asyncio.run(generate_suggestions_service(transcript=plain_text))
                if "error" in suggestions:
                    logger.warning(f"Job {current_job_id}: LLM service returned an error: {suggestions.get('error')} - {suggestions.get('details')}")
                else:
                    title = suggestions.get('titles')[0] if suggestions.get('titles') else None # Take first title
                    summary = suggestions.get('summary')

                    if title or summary: # Check if at least one was generated
                        logger.info(f"Job {current_job_id}: LLM suggestions generated. Title: {title}, Summary: {summary}")
                        db_job.generated_title = title
                        db_job.generated_summary = summary
                        db.commit()
                        db.refresh(db_job)
                    else:
                        logger.warning(f"Job {current_job_id}: LLM service generated no usable suggestions (empty title/summary).")
            except Exception as llm_exc:
                logger.error(f"Job {current_job_id}: Error during LLM suggestion generation: {llm_exc}", exc_info=True)
                # Do not let LLM failure fail the whole job if transcription was successful. Log and continue.
        else:
            logger.info(f"Job {current_job_id}: No transcript text available, skipping LLM suggestions.")

        db_job.status = JobStatus.COMPLETED
        db.commit()
        logger.info(f"Job {current_job_id}: Processing complete for {original_filename}")
        # BaseTaskWithDB on_success will log if this task returns.
        # Return value could be dict of paths or job_id.
        return {"job_id": current_job_id, "status": "COMPLETED", "normalized_audio": str(db_job.output_file_path)}

    except Exception as e:
        logger.error(f"Error processing file {file_path_str} (Job ID {db_job.id if db_job else 'N/A'}): {e}", exc_info=True)
        if db_job: # Check if db_job was successfully created/fetched
            db_job.status = JobStatus.FAILED
            db_job.error_message = str(e)[:1000] # Truncate error message if too long for DB field
            db.commit()
        # Re-raise so BaseTaskWithDB on_failure can also log it.
        # Pass current_job_id if available, so BaseTaskWithDB can use it.
        # This part is tricky because BaseTaskWithDB expects job_id as first arg to the task,
        # or as a kwarg 'job_id'. Our task signature is (file_path_str, username).
        # The self.request.id in BaseTaskWithDB is Celery's task ID, not our ProcessingJob.id.
        # For now, BaseTaskWithDB's job update on failure might not work correctly for this task
        # as it doesn't receive job_id in the expected way.
        # The explicit update above is the primary error handling for job status.
        raise
    finally:
        db.close()

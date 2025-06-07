"""Wrapper for interacting with n8n workflows."""

import httpx
import logging
from pathlib import Path
from sqlalchemy.orm import Session # Required for type hinting and DB interaction
from typing import Dict, Any # Ensure Any is imported

from backend.app.config import settings # N8N_WEBHOOK_URL and N8N_API_KEY
from backend.app.models.job import ProcessingJob, JobStatus # For type hinting
from backend.app.models.llm import LLMSuggestion # For fetching suggestions
from backend.app.utils.storage import DATA_ROOT # To construct full paths if needed

# Get a logger for this module
logger = logging.getLogger(__name__)

async def trigger_n8n_workflow(job: ProcessingJob, db: Session) -> Dict[str, Any]:
    """
    Triggers an n8n workflow with data from a completed ProcessingJob.

    Args:
        job: The completed ProcessingJob object.
        db: The SQLAlchemy database session, used to fetch related data like LLM suggestions.

    Returns:
        A dictionary indicating success or failure, and any response from n8n.
        Example success: {"success": True, "message": "...", "n8n_response": ...}
        Example failure: {"success": False, "message": "...", "details": ...}
    
    Raises:
        ValueError: If N8N_WEBHOOK_URL is not configured.
        httpx.HTTPStatusError: If n8n returns an HTTP error status.
        httpx.RequestError: For other request-related issues (e.g., connection error).
        Exception: For other unexpected errors during the process.
    """
    if not settings.N8N_WEBHOOK_URL:
        logger.error("N8N_WEBHOOK_URL is not configured. Cannot trigger n8n workflow.")
        # This error should ideally be caught by the API layer and returned as a 503 or similar.
        raise ValueError("n8n webhook URL is not configured in settings.")

    logger.info(f"Preparing to trigger n8n workflow for job_id: {job.id} (Type: {job.job_type})")

    # --- 1. Gather Data for n8n Payload ---
    media_file_path_relative = job.output_file_path
    media_file_path_absolute = DATA_ROOT / media_file_path_relative if media_file_path_relative else None
    logger.debug(f"Job {job.id}: Media file relative path: {media_file_path_relative}, Absolute: {media_file_path_absolute}")

    media_type = "unknown"
    if job.job_type == "video_generation" and media_file_path_absolute and media_file_path_absolute.suffix == ".mp4":
        media_type = "video"
    elif job.job_type == "audio_processing" and media_file_path_absolute and media_file_path_absolute.suffix == ".mp3":
        media_type = "audio"
    logger.debug(f"Job {job.id}: Determined media type: {media_type}")

    # Fetch latest LLM suggestions for this job
    llm_suggestion = db.query(LLMSuggestion).filter(LLMSuggestion.job_id == job.id).order_by(LLMSuggestion.created_at.desc()).first()
    
    title = None
    summary = None
    if llm_suggestion:
        titles = llm_suggestion.get_titles() # Uses the helper method in LLMSuggestion model
        if titles:
            title = titles[0] # Use the first suggested title
        summary = llm_suggestion.suggested_summary
        logger.info(f"Job {job.id}: Found LLM suggestion {llm_suggestion.id}. Title: '{title}', Summary: '{summary}'")
    else:
        logger.warning(f"Job {job.id}: No LLM suggestions found.")

    # Fetch transcript paths (SRT and TXT)
    # This logic assumes that if an LLM suggestion exists and is linked to a transcription job, that's the relevant transcript.
    # If the current job IS the transcription job, use its output.
    transcript_srt_path_relative = None
    transcript_txt_path_relative = None

    source_transcription_job_id = None
    if job.job_type == "transcription":
        source_transcription_job_id = job.id
    elif llm_suggestion and llm_suggestion.job and llm_suggestion.job.job_type == "transcription":
        source_transcription_job_id = llm_suggestion.job.id
    
    if source_transcription_job_id:
        transcription_job_for_paths = db.query(ProcessingJob).filter(ProcessingJob.id == source_transcription_job_id).first()
        if transcription_job_for_paths and transcription_job_for_paths.output_file_path:
            transcript_srt_path_relative = transcription_job_for_paths.output_file_path
            transcript_txt_path_relative = str(Path(transcript_srt_path_relative).with_suffix(".txt"))
            logger.info(f"Job {job.id}: Found transcript from job {source_transcription_job_id}. SRT: {transcript_srt_path_relative}")
        else:
            logger.warning(f"Job {job.id}: Could not retrieve transcript paths from supposed source job {source_transcription_job_id}.")
    else:
        logger.warning(f"Job {job.id}: No clear source transcription job found for transcript paths.")

    # --- 2. Construct n8n Payload ---
    payload = {
        "job_id": job.id,
        "job_type": job.job_type,
        "media_type": media_type,
        # Paths should be absolute for n8n if it's running in a different container but sharing the /data volume
        "media_file_path": str(media_file_path_absolute) if media_file_path_absolute else None,
        "title": title,
        "summary": summary,
        "transcript_srt_path": str(DATA_ROOT / transcript_srt_path_relative) if transcript_srt_path_relative else None,
        "transcript_txt_path": str(DATA_ROOT / transcript_txt_path_relative) if transcript_txt_path_relative else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "source_input_file_path": str(DATA_ROOT / job.input_file_path) if job.input_file_path else None,
    }
    logger.debug(f"Job {job.id}: Payload for n8n: {payload}")

    # --- 3. Send Request to n8n ---
    headers = {}
    if settings.N8N_API_KEY:
        # n8n webhook node can be configured to use various auth methods.
        # "Header Auth" is common. The header name is defined in n8n.
        # 'X-N8N-API-KEY' is a placeholder; adjust to actual n8n webhook config.
        headers["X-N8N-API-KEY"] = settings.N8N_API_KEY 
        logger.debug(f"Job {job.id}: Using API key for n8n request.")

    async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout
        try:
            logger.info(f"Job {job.id}: Sending POST request to n8n webhook: {settings.N8N_WEBHOOK_URL}")
            response = await client.post(settings.N8N_WEBHOOK_URL, json=payload, headers=headers)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            
            n8n_response_data = response.json()
            logger.info(f"n8n workflow triggered successfully for job_id: {job.id}. n8n response: {n8n_response_data}")
            return {
                "success": True,
                "message": "n8n workflow triggered successfully.",
                "n8n_response": n8n_response_data
            }
        except httpx.HTTPStatusError as e:
            error_body = e.response.text if e.response else "No response body."
            logger.error(f"HTTP error {e.response.status_code} from n8n for job_id {job.id}: {error_body}", exc_info=True)
            # Return a structured error instead of re-raising directly, to be handled by API layer
            return {
                "success": False,
                "message": f"HTTP error from n8n: {e.response.status_code}",
                "details": error_body
            }
        except httpx.RequestError as e:
            logger.error(f"Request error for n8n (URL: {e.request.url}) for job_id {job.id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Request to n8n failed.",
                "details": str(e)
            }
        except Exception as e:
            logger.error(f"An unexpected error occurred in trigger_n8n_workflow for job_id {job.id}: {e}", exc_info=True)
            return {
                "success": False,
                "message": "An unexpected error occurred while triggering n8n workflow.",
                "details": str(e)
            }

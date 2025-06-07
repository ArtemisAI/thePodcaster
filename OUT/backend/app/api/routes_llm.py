"""Endpoints that interact with the local LLM via Ollama."""

# Planned endpoints:
# * POST /ai/suggest – Provide transcript; returns title & summary.
#   Body: {"transcript_id": int, "tone": "clickbaity|formal|casual"}

# Endpoints for generating suggestions via LLM (Ollama).
from fastapi import APIRouter, Request, HTTPException, status
from pathlib import Path

from ..db.database import SessionLocal
from ..models.job import ProcessingJob, JobStatus
from ..models.llm import LLMSuggestion
from ..services.llm import generate_suggestions
from ..utils.storage import DATA_ROOT
from ..config import settings

router = APIRouter()

async def read_transcript_from_job(job: ProcessingJob) -> str:
    """Read the transcript SRT file for a completed transcription job."""
    transcript_path = DATA_ROOT / job.output_file_path
    if not Path(transcript_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript file not found for job {job.id}",
        )
    # Read file contents
    content = Path(transcript_path).read_text(encoding="utf-8")
    return content

@router.post("/suggest/from_job/{job_id}")
async def suggest_from_job(job_id: int, prompt_type: str = "title_summary") -> dict:
    """Generate LLM suggestions based on a completed transcription job."""
    db = SessionLocal()
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing job with ID {job_id} not found",
        )
    if job.job_type != "transcription":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not a transcription job",
        )
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job has not yet completed",
        )
    transcript = await read_transcript_from_job(job)
    if not transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transcript for job {job_id} is empty",
        )
    try:
        suggestions = await generate_suggestions(transcript, prompt_type)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate LLM suggestions: {e}",
        )
    if isinstance(suggestions, dict) and suggestions.get("error"):
        detail = suggestions.get("details") or suggestions.get("error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error from LLM service: {detail}",
        )
    # Persist suggestion
    suggestion = LLMSuggestion(
        job_id=job.id,
        prompt_type=prompt_type,
        model_used=settings.OLLAMA_DEFAULT_MODEL,
        titles=suggestions.get("titles"),
        suggested_summary=suggestions.get("summary"),
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return {
        "job_id": suggestion.job_id,
        "prompt_type": suggestion.prompt_type,
        "titles": suggestion.get_titles(),
        "summary": suggestion.suggested_summary,
        "model_used": suggestion.model_used,
    }

@router.post("/suggest/from_text")
async def suggest_from_text(request: Request, prompt_type: str = "title_summary", transcript_text: str | None = None) -> dict:
    """Generate LLM suggestions based on provided raw transcript text."""
    # Determine transcript text from query or raw body
    if transcript_text is None:
        body_bytes = await request.body()
        transcript_text = body_bytes.decode("utf-8")
    if not transcript_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript text is empty",
        )
    try:
        suggestions = await generate_suggestions(transcript_text, prompt_type)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate LLM suggestions: {e}",
        )
    if isinstance(suggestions, dict) and suggestions.get("error"):
        detail = suggestions.get("details") or suggestions.get("error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error from LLM service: {detail}",
        )
    # Persist suggestion
    db = SessionLocal()
    suggestion = LLMSuggestion(
        job_id=None,
        prompt_type=prompt_type,
        model_used=settings.OLLAMA_DEFAULT_MODEL,
        titles=suggestions.get("titles"),
        suggested_summary=suggestions.get("summary"),
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return {
        "prompt_type": suggestion.prompt_type,
        "titles": suggestion.get_titles(),
        "summary": suggestion.suggested_summary,
        "model_used": suggestion.model_used,
    }

@router.get("/suggestions/{suggestion_id}")
async def get_suggestion(suggestion_id: int) -> dict:
    """Retrieve a specific LLM suggestion by its ID."""
    db = SessionLocal()
    suggestion = db.query(LLMSuggestion).filter(LLMSuggestion.id == suggestion_id).first()
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )
    return {
        "suggestion_id": suggestion.id,
        "job_id": suggestion.job_id,
        "prompt_type": suggestion.prompt_type,
        "titles": suggestion.get_titles(),
        "summary": suggestion.suggested_summary,
        "model_used": suggestion.model_used,
    }

@router.get("/suggestions/by_job/{job_id}")
async def get_suggestions_by_job(job_id: int) -> list:
    """Retrieve all LLM suggestions associated with a given job ID."""
    db = SessionLocal()
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Processing job with ID {job_id} not found",
        )
    suggestions = db.query(LLMSuggestion).filter(LLMSuggestion.job_id == job_id).all()
    results = []
    for s in suggestions:
        results.append({
            "suggestion_id": s.id,
            "titles": s.get_titles(),
            "summary": s.suggested_summary,
        })
    return results

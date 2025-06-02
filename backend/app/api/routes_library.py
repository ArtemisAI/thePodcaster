from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request # Import Request
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.job import ProcessingJob, JobStatus, JobType
from app.models.transcript import Transcript
from app.models.llm import LLMSuggestion

# Pydantic models for API response
from pydantic import BaseModel, HttpUrl
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models ---

class LibraryItemTranscript(BaseModel):
    id: int
    language: Optional[str] = None
    text_content_url: Optional[HttpUrl] = None # URL to download .txt
    srt_content_url: Optional[HttpUrl] = None # URL to download .srt

class LibraryItemLLMSuggestion(BaseModel):
    id: int
    prompt_type: str
    model_used: Optional[str] = None
    titles: Optional[List[str]] = None
    summary: Optional[str] = None

class LibraryItem(BaseModel):
    job_id: int
    job_type: str # Using str representation of JobType enum
    status: str  # Using str representation of JobStatus enum
    created_at: datetime
    output_file_url: Optional[HttpUrl] = None
    generated_title: Optional[str] = None
    generated_summary: Optional[str] = None # From ProcessingJob model directly
    transcript: Optional[LibraryItemTranscript] = None
    llm_suggestions: Optional[LibraryItemLLMSuggestion] = None # Could be a list if multiple suggestions per job are possible
    # Add fields for original uploaded files if necessary

class PaginatedLibraryItems(BaseModel):
    items: List[LibraryItem]
    total: int
    page: int
    size: int

# --- Helper Functions ---

def resolve_output_file_url(job: ProcessingJob, request: Request) -> Optional[str]:
    if job.output_file_path:
        # Assuming output_file_path is just the filename.
        # Construct URL relative to an assumed /api/outputs/ endpoint.
        # This might need to be adjusted if you use request.url_for with a named route.
        # For example, if you have a route named "get_output_file" that takes a filename:
        # try:
        #     return str(request.url_for("get_output_file", filename=job.output_file_path))
        # except Exception as e:
        #     logger.error(f"Failed to generate URL for output file: {e}")
        #     return None # Or a static placeholder
        return f"{str(request.base_url).rstrip('/')}/api/outputs/{job.output_file_path}"
    return None

# --- API Endpoints ---

@router.get("/items", response_model=PaginatedLibraryItems)
async def list_library_items(
    request: Request, # Added Request
    db: Session = Depends(get_db),
    page: int = 1,
    size: int = 20,
    # TODO: Add filtering options (e.g., by job_type, status)
    # TODO: Review job_type filter logic for primary library items.
):
    # For a library, we are primarily interested in completed jobs that produced a final artifact.
    query = (
        db.query(ProcessingJob)
        .options(
            joinedload(ProcessingJob.transcripts).subqueryload('*'), # Load transcripts
            joinedload(ProcessingJob.llm_suggestions_collection).subqueryload('*') # Load LLM suggestions
        )
        .filter(ProcessingJob.status == JobStatus.COMPLETED) # Focus on completed jobs
        .filter(ProcessingJob.job_type.in_([
            JobType.FILEBROWSER_AUDIO_UPLOAD,
            JobType.AUDIO_CONCATENATION,
            JobType.VIDEO_GENERATION,
            JobType.TRANSCRIPTION # Included for now, but review if these should be top-level items
        ]))
        .order_by(ProcessingJob.created_at.desc())
    )

    total = query.count()
    items_db = query.offset((page - 1) * size).limit(size).all()

    library_items = []
    for job in items_db:
        transcript_data = None
        if job.transcripts:
            # Assuming we take the first transcript if multiple exist.
            # Consider sorting by creation date if relevant (e.g., job.transcripts.sort(key=lambda t: t.created_at, reverse=True))
            transcript_obj = job.transcripts[0]
            # TODO: Implement actual transcript content endpoints in routes_transcription.py
            # These URLs are placeholders and assume routes like /api/transcription/{id}/text and /srt exist.
            transcript_data = LibraryItemTranscript(
                id=transcript_obj.id,
                language=transcript_obj.language,
                text_content_url=f"{str(request.base_url).rstrip('/')}/api/transcription/{transcript_obj.id}/text",
                srt_content_url=f"{str(request.base_url).rstrip('/')}/api/transcription/{transcript_obj.id}/srt"
            )

        llm_data = None
        if job.llm_suggestions_collection:
            # Assuming we take the first LLM suggestion if multiple exist.
            # Consider sorting or other logic if needed.
            llm_obj = job.llm_suggestions_collection[0]
            llm_data = LibraryItemLLMSuggestion(
                id=llm_obj.id,
                prompt_type=llm_obj.prompt_type,
                model_used=llm_obj.model_used,
                titles=llm_obj.get_titles(), # Assuming get_titles() is a method on LLMSuggestion model
                summary=llm_obj.suggested_summary
            )

        item = LibraryItem(
            job_id=job.id,
            job_type=job.job_type_str,
            status=job.status_str,
            created_at=job.created_at,
            output_file_url=resolve_output_file_url(job, request),
            generated_title=job.generated_title,
            generated_summary=job.generated_summary,
            transcript=transcript_data,
            llm_suggestions=llm_data,
        )
        library_items.append(item)

    return PaginatedLibraryItems(items=library_items, total=total, page=page, size=size)


@router.get("/items/{item_id}", response_model=LibraryItem)
async def get_library_item(item_id: int, request: Request, db: Session = Depends(get_db)): # Added Request
    job = (
        db.query(ProcessingJob)
        .options(
            joinedload(ProcessingJob.transcripts).subqueryload('*'), # Load transcripts
            joinedload(ProcessingJob.llm_suggestions_collection).subqueryload('*') # Load LLM suggestions
        )
        .filter(ProcessingJob.id == item_id)
        .first()
    )

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library item not found")

    transcript_data = None
    if job.transcripts:
        # Assuming we take the first transcript.
        transcript_obj = job.transcripts[0]
        # TODO: Implement actual transcript content endpoints in routes_transcription.py
        transcript_data = LibraryItemTranscript(
            id=transcript_obj.id,
            language=transcript_obj.language,
            text_content_url=f"{str(request.base_url).rstrip('/')}/api/transcription/{transcript_obj.id}/text",
            srt_content_url=f"{str(request.base_url).rstrip('/')}/api/transcription/{transcript_obj.id}/srt"
        )

    llm_data = None
    if job.llm_suggestions_collection:
        # Assuming we take the first LLM suggestion.
        llm_obj = job.llm_suggestions_collection[0]
        llm_data = LibraryItemLLMSuggestion(
            id=llm_obj.id,
            prompt_type=llm_obj.prompt_type,
            model_used=llm_obj.model_used,
            titles=llm_obj.get_titles(),
            summary=llm_obj.suggested_summary
        )

    return LibraryItem(
        job_id=job.id,
        job_type=job.job_type_str,
        status=job.status_str,
        created_at=job.created_at,
        output_file_url=resolve_output_file_url(job, request),
        generated_title=job.generated_title,
        generated_summary=job.generated_summary,
        transcript=transcript_data,
        llm_suggestions=llm_data,
    )

# Note: The joinedload paths ProcessingJob.transcripts and ProcessingJob.llm_suggestions_collection
# were confirmed/updated in the previous subtask by modifying the respective models.
# The .subqueryload('*') is added to potentially avoid N+1 issues on accessing attributes of related objects,
# though for simple first-item access like job.transcripts[0].language, it might not be strictly necessary
# compared to just joinedload(). It's a good practice for more complex access patterns.

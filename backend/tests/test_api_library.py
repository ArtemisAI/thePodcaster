from __future__ import annotations

from typing import List, Optional, Any
from datetime import datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job import ProcessingJob, JobStatus, JobType
from app.models.transcript import Transcript
from app.models.llm import LLMSuggestion
from app.db.database import Base, engine # For creating test schema
from app.main import app # To get the TestClient

# Use a separate test database or ensure transactions roll back
# For this example, we'll recreate the schema for each test session if needed,
# but a more robust setup might use a dedicated test DB or transaction management.

# Test client fixture
@pytest.fixture(scope="module")
def client() -> TestClient:
    # Create tables for in-memory SQLite if they don't exist (for local testing)
    # In a real CI, the test DB would be managed separately.
    # This is now handled in conftest.py, but leaving it here won't harm.
    Base.metadata.create_all(bind=engine) # Ensure schema is created
    return TestClient(app)

@pytest.fixture(autouse=True)
def clear_data(db: Session):
    # Clear relevant tables before each test to ensure isolation
    db.query(LLMSuggestion).delete()
    db.query(Transcript).delete()
    db.query(ProcessingJob).delete()
    db.commit()

# Helper to create a ProcessingJob with optional related items
def create_job_in_db(
    db: Session,
    job_type: JobType = JobType.AUDIO_CONCATENATION,
    status: JobStatus = JobStatus.COMPLETED,
    output_file_path: Optional[str] = None,
    created_at: Optional[datetime] = None,
    generated_title: Optional[str] = None,
    generated_summary: Optional[str] = None,
    add_transcript: bool = False,
    add_llm_suggestion: bool = False,
) -> ProcessingJob:
    if created_at is None:
        created_at = datetime.utcnow()
    if output_file_path is None:
        output_file_path = f"test_output_{created_at.timestamp()}.mp3"

    job = ProcessingJob(
        job_type=job_type,
        status=status,
        output_file_path=output_file_path,
        created_at=created_at,
        generated_title=generated_title,
        generated_summary=generated_summary,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if add_transcript:
        transcript = Transcript(
            processing_job_id=job.id,
            text_content="This is a test transcript.",
            srt_content="1\n00:00:01,000 --> 00:00:02,000\nTest line.",
            language="en",
            created_at=job.created_at,
        )
        db.add(transcript)
        db.commit()
        db.refresh(transcript)

    if add_llm_suggestion:
        llm_suggestion = LLMSuggestion(
            job_id=job.id,
            prompt_type="test_prompt",
            model_used="test_model",
            titles=["Test Title 1", "Test Title 2"],
            suggested_summary="This is a test LLM summary.",
            created_at=job.created_at,
        )
        db.add(llm_suggestion)
        db.commit()
        db.refresh(llm_suggestion)
    
    db.refresh(job) # Refresh job again to load relationships
    return job

# --- Test Cases ---

def test_list_library_items_empty(client: TestClient, db: Session):
    response = client.get("/api/library/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["size"] == 20

def test_list_library_items_single_item(client: TestClient, db: Session):
    job_time = datetime.utcnow()
    create_job_in_db(
        db,
        created_at=job_time,
        output_file_path="item1.mp3",
        generated_title="My First Episode"
    )

    response = client.get("/api/library/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["job_id"] is not None
    assert item["job_type"] == JobType.AUDIO_CONCATENATION.value
    assert item["status"] == JobStatus.COMPLETED.value
    assert item["generated_title"] == "My First Episode"
    assert "item1.mp3" in item["output_file_url"] # Check if filename is in URL
    # Basic check for datetime string format
    assert datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")).year == job_time.year

def test_list_library_items_with_transcript_and_llm(client: TestClient, db: Session):
    create_job_in_db(db, add_transcript=True, add_llm_suggestion=True, generated_title="Full Item")

    response = client.get("/api/library/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["generated_title"] == "Full Item"
    
    assert item["transcript"] is not None
    assert item["transcript"]["id"] is not None
    assert item["transcript"]["language"] == "en"
    assert "/api/transcription/" in item["transcript"]["text_content_url"]
    assert "/text" in item["transcript"]["text_content_url"]
    assert "/api/transcription/" in item["transcript"]["srt_content_url"]
    assert "/srt" in item["transcript"]["srt_content_url"]

    assert item["llm_suggestions"] is not None
    assert item["llm_suggestions"]["id"] is not None
    assert item["llm_suggestions"]["prompt_type"] == "test_prompt"
    assert "Test Title 1" in item["llm_suggestions"]["titles"]
    assert item["llm_suggestions"]["summary"] == "This is a test LLM summary."


def test_list_library_items_pagination(client: TestClient, db: Session):
    for i in range(25): # Create 25 items
        create_job_in_db(db, created_at=datetime.utcnow() - timedelta(seconds=i), output_file_path=f"item_{i}.mp3")

    # Test first page
    response_p1 = client.get("/api/library/items?page=1&size=10")
    assert response_p1.status_code == status.HTTP_200_OK
    data_p1 = response_p1.json()
    assert data_p1["total"] == 25
    assert len(data_p1["items"]) == 10
    assert data_p1["page"] == 1
    assert data_p1["size"] == 10

    # Test second page
    response_p2 = client.get("/api/library/items?page=2&size=10")
    assert response_p2.status_code == status.HTTP_200_OK
    data_p2 = response_p2.json()
    assert len(data_p2["items"]) == 10

    # Test last page (partial)
    response_p3 = client.get("/api/library/items?page=3&size=10")
    assert response_p3.status_code == status.HTTP_200_OK
    data_p3 = response_p3.json()
    assert len(data_p3["items"]) == 5 # Remaining 5

    # Ensure items are different across pages (simple check based on output_file_url)
    assert data_p1["items"][0]["output_file_url"] != data_p2["items"][0]["output_file_url"]

def test_get_library_item_not_found(client: TestClient, db: Session):
    response = client.get("/api/library/items/99999") # Non-existent ID
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_get_library_item_success(client: TestClient, db: Session):
    job = create_job_in_db(
        db,
        generated_title="Specific Item",
        add_transcript=True,
        add_llm_suggestion=True
    )

    response = client.get(f"/api/library/items/{job.id}")
    assert response.status_code == status.HTTP_200_OK
    item = response.json()

    assert item["job_id"] == job.id
    assert item["generated_title"] == "Specific Item"
    assert item["transcript"] is not None
    assert item["transcript"]["id"] is not None # The transcript object should have its own ID
    assert item["llm_suggestions"] is not None
    assert item["llm_suggestions"]["id"] is not None # The LLM suggestion object should have its own ID

# TODO: Add tests for filtering if/when implemented (e.g., by job_type, status not COMPLETED if that's supported)
# TODO: Add tests to verify correct URL construction with a non-default base_url if possible with TestClient.

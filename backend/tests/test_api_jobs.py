import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.main import app
from app.models.job import ProcessingJob, JobStatus

client = TestClient(app)


@patch("app.api.routes_jobs.SessionLocal")
def test_list_jobs(mock_session_local):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_db.query.return_value.order_by.return_value.all.return_value = [
        ProcessingJob(id=1, job_type="audio_processing", status=JobStatus.PENDING, created_at=datetime.utcnow()),
        ProcessingJob(id=2, job_type="video_generation", status=JobStatus.COMPLETED, output_file_path="processed/2.mp4", created_at=datetime.utcnow()),
    ]

    response = client.get("/api/jobs")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[1]["id"] == 2


@patch("app.api.routes_jobs.SessionLocal")
def test_get_job(mock_session_local):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_job = ProcessingJob(id=5, job_type="audio_processing", status=JobStatus.COMPLETED, output_file_path="processed/5.mp3", created_at=datetime.utcnow())
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job

    response = client.get("/api/jobs/5")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["output_file_path"] == "processed/5.mp3"

import pytest
from httpx import AsyncClient
from fastapi import FastAPI, UploadFile, status
from unittest.mock import patch, MagicMock, AsyncMock
import io
from pathlib import Path

# Import your FastAPI app instance
# This assumes your app is created in backend.app.main.py
from backend.app.main import app 
from backend.app.models.job import JobStatus, ProcessingJob # For type hinting and creating mock objects
from backend.app.db.database import get_db # To override for test DB if needed

# --- Test Setup & Fixtures ---

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# In-memory SQLite DB for testing (optional, can mock DB calls directly)
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from backend.app.db.database import Base
# TEST_DATABASE_URL = "sqlite:///:memory:"
# engine = create_engine(TEST_DATABASE_URL)
# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# @pytest.fixture(scope="function")
# def db_session():
#     Base.metadata.create_all(bind=engine)
#     db = TestingSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#         Base.metadata.drop_all(bind=engine)

# def override_get_db():
#     try:
#         db = TestingSessionLocal()
#         yield db
#     finally:
#         db.close()
# app.dependency_overrides[get_db] = override_get_db


# Helper to create a dummy UploadFile
def create_dummy_upload_file(filename: str, content: bytes = b"dummy content") -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))

# --- Test Cases ---

@pytest.mark.asyncio
@patch("backend.app.api.routes_audio.save_uploaded_file")
async def test_upload_audio_main_track_only(mock_save_file, client: AsyncClient):
    mock_save_file.return_value = Path("/data/uploads/test_session_id/dummy_main.mp3")
    
    files = {"main_track": ("dummy_main.mp3", b"main content", "audio/mpeg")}
    
    response = await client.post("/api/audio/upload", files=files)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "upload_session_id" in data
    assert "saved_files" in data
    assert "main_track" in data["saved_files"]
    mock_save_file.assert_called_once()


@pytest.mark.asyncio
@patch("backend.app.api.routes_audio.save_uploaded_file")
async def test_upload_audio_all_tracks(mock_save_file, client: AsyncClient):
    # Simulate different return paths for each call if needed, or a generic one
    mock_save_file.side_effect = [
        Path("/data/uploads/test_session_id/main.mp3"),
        Path("/data/uploads/test_session_id/intro.mp3"),
        Path("/data/uploads/test_session_id/outro.mp3"),
    ]
    
    files = {
        "main_track": ("main.mp3", b"main", "audio/mpeg"),
        "intro": ("intro.mp3", b"intro", "audio/mpeg"),
        "outro": ("outro.mp3", b"outro", "audio/mpeg"),
    }
    
    response = await client.post("/api/audio/upload", files=files)
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "upload_session_id" in data
    assert "main_track" in data["saved_files"]
    assert "intro" in data["saved_files"]
    assert "outro" in data["saved_files"]
    assert mock_save_file.call_count == 3


@pytest.mark.asyncio
async def test_upload_audio_missing_main_track(client: AsyncClient):
    files = {"intro": ("intro.mp3", b"intro", "audio/mpeg")} # No main_track
    response = await client.post("/api/audio/upload", files=files)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@patch("backend.app.api.routes_audio.process_audio_task.delay", new_callable=AsyncMock) # Mock Celery task
@patch("backend.app.api.routes_audio.UPLOAD_DIR", Path("/data/uploads")) # Ensure UPLOAD_DIR is a Path
@patch("backend.app.api.routes_audio.Path.exists") # Mock Path.exists
@patch("backend.app.api.routes_audio.Path.glob") # Mock Path.glob
@patch("backend.app.db.database.SessionLocal") # Mock the DB session
async def test_process_audio_success(mock_session_local, mock_glob, mock_exists, mock_celery_delay, client: AsyncClient):
    mock_db_instance = MagicMock()
    mock_session_local.return_value = mock_db_instance # Return a mock session

    mock_exists.return_value = True # Assume session directory exists
    # Simulate files being found by glob
    mock_file_in_session = MagicMock(spec=Path)
    mock_file_in_session.is_file.return_value = True
    mock_file_in_session.relative_to.return_value = Path("uploads/test_session/dummy.mp3")
    mock_glob.return_value = [mock_file_in_session]

    upload_session_id = "test_session_id_process"
    
    response = await client.post(f"/api/audio/process/{upload_session_id}")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "job_id" in data
    assert data["message"] == "Audio processing started."
    
    mock_db_instance.add.assert_called_once()
    mock_db_instance.commit.assert_called_once()
    mock_db_instance.refresh.assert_called_once()
    mock_celery_delay.assert_called_once()
    # Check some args of celery delay if necessary
    args, kwargs = mock_celery_delay.call_args
    assert kwargs['job_id'] is not None
    assert "uploads/test_session/dummy.mp3" in kwargs['input_paths_str']


@pytest.mark.asyncio
@patch("backend.app.api.routes_audio.UPLOAD_DIR", Path("/data/uploads")) # Ensure UPLOAD_DIR is a Path
@patch("backend.app.api.routes_audio.Path.exists")
async def test_process_audio_session_not_found(mock_exists, client: AsyncClient):
    mock_exists.return_value = False # Session directory does not exist
    upload_session_id = "non_existent_session"
    response = await client.post(f"/api/audio/process/{upload_session_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("backend.app.db.database.SessionLocal")
async def test_get_job_status_found(mock_session_local, client: AsyncClient):
    mock_db_instance = MagicMock()
    mock_session_local.return_value = mock_db_instance

    mock_job = ProcessingJob(id=1, job_type="audio_processing", status=JobStatus.COMPLETED, output_file_path="processed/output.mp3")
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_job
    mock_db_instance.query.return_value = mock_query
    
    response = await client.get("/api/audio/status/1")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["job_id"] == 1
    assert data["status"] == "COMPLETED"
    assert data["output_file_path"] == "processed/output.mp3"


@pytest.mark.asyncio
@patch("backend.app.db.database.SessionLocal")
async def test_get_job_status_not_found(mock_session_local, client: AsyncClient):
    mock_db_instance = MagicMock()
    mock_session_local.return_value = mock_db_instance
    
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None # Job not found
    mock_db_instance.query.return_value = mock_query

    response = await client.get("/api/audio/status/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@patch("backend.app.db.database.SessionLocal")
@patch("backend.app.api.routes_audio.FileResponse") # Mock FileResponse
@patch("backend.app.api.routes_audio.PROCESSED_DIR", Path("/data/processed")) # Ensure PROCESSED_DIR is Path
@patch("backend.app.api.routes_audio.Path.exists") # Mock Path.exists for the file itself
async def test_download_processed_audio_completed(mock_path_exists, mock_file_response, mock_session_local, client: AsyncClient):
    mock_db_instance = MagicMock()
    mock_session_local.return_value = mock_db_instance

    mock_job = ProcessingJob(id=1, job_type="audio_processing", status=JobStatus.COMPLETED, output_file_path="processed/output.mp3")
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_job
    mock_db_instance.query.return_value = mock_query
    
    mock_path_exists.return_value = True # Processed file exists
    mock_file_response_instance = MagicMock()
    mock_file_response.return_value = mock_file_response_instance # Return a mock response object
                                                                # This isn't strictly necessary unless you check its properties

    response = await client.get("/api/audio/download/1")
    
    # If FileResponse is mocked, the actual response might not be what a real FileResponse is.
    # We are testing that FileResponse is *called* correctly.
    # The status code here will be from the FastAPI test client if FileResponse is fully mocked.
    assert response.status_code == status.HTTP_200_OK 
    mock_file_response.assert_called_once()
    args, kwargs = mock_file_response.call_args
    assert kwargs['path'] == Path("/data/processed/output.mp3") # Check it's using the full absolute path
    assert kwargs['filename'] == "output.mp3"


@pytest.mark.asyncio
@patch("backend.app.db.database.SessionLocal")
async def test_download_processed_audio_not_completed(mock_session_local, client: AsyncClient):
    mock_db_instance = MagicMock()
    mock_session_local.return_value = mock_db_instance

    mock_job = ProcessingJob(id=2, job_type="audio_processing", status=JobStatus.PROCESSING)
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_job
    mock_db_instance.query.return_value = mock_query
    
    response = await client.get("/api/audio/download/2")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@patch("backend.app.db.database.SessionLocal")
@patch("backend.app.api.routes_audio.PROCESSED_DIR", Path("/data/processed"))
@patch("backend.app.api.routes_audio.Path.exists")
async def test_download_processed_audio_file_not_found_on_server(mock_path_exists, mock_session_local, client: AsyncClient):
    mock_db_instance = MagicMock()
    mock_session_local.return_value = mock_db_instance

    mock_job = ProcessingJob(id=3, job_type="audio_processing", status=JobStatus.COMPLETED, output_file_path="processed/missing.mp3")
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = mock_job
    mock_db_instance.query.return_value = mock_query

    mock_path_exists.return_value = False # Simulate file not existing on disk
    
    response = await client.get("/api/audio/download/3")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Processed file not found on server" in response.json()["detail"]

# To run these tests:
# 1. Ensure you are in the `backend` directory.
# 2. Run `python -m pytest`
# You might need to set PYTHONPATH=. if you have import issues, e.g., `PYTHONPATH=. python -m pytest`
# Ensure all necessary dependencies from requirements.txt are installed in your test environment.
# Also, ensure the FastAPI application `app` can be imported correctly.
# For tests involving database (like get_job_status), if not using override_get_db with an in-memory SQLite,
# ensure your development database is accessible, or mock the db session more thoroughly.
# The mocks for SessionLocal provide a basic way to avoid direct DB calls for these unit tests.
# Consider using a more robust test DB setup for integration tests.
# The UPLOAD_DIR and PROCESSED_DIR mocks are important if they are used to construct paths in the route.
# Path.exists and Path.glob are mocked for the /process endpoint to simulate file system checks.
# FileResponse is mocked for /download to avoid issues with actual file serving during unit tests.
# Celery task's .delay method is mocked for /process to prevent actual task queuing.
# save_uploaded_file is mocked for /upload to prevent file system writes.
# Remember to ensure your main app (`backend.app.main.app`) does not perform DB initialization
# or other side effects at import time that could interfere with tests, or mock those out too.
# (e.g., if init_db() is called at module level in main.py, that could be an issue).
# Ideally, app setup (like DB init, Celery app config) is done within functions or conditional blocks.
# The current FastAPI app structure with `create_app` is generally test-friendly.
# The `client` fixture from `httpx.AsyncClient` is the standard way to test FastAPI apps.
# Base URL "http://test" is conventional for `AsyncClient`.
# For `test_process_audio_success`, the `UPLOAD_DIR` patch and `Path.glob` mock are crucial.
# `Path.relative_to` is also implicitly part of what `mock_file_in_session.relative_to.return_value` covers.
# The DB session mocking (`@patch("backend.app.db.database.SessionLocal")`) is a common way to unit test
# FastAPI endpoints that use `Depends(get_db)` without hitting a real database.
# You create a MagicMock for the session, then mock its `query().filter().first()` chain.
# `mock_db_instance.add.assert_called_once()` etc. verify that ORM methods are called.
# `mock_celery_delay.assert_called_once()` verifies the Celery task was dispatched.
# For tests involving paths (UPLOAD_DIR, PROCESSED_DIR), ensure they are `pathlib.Path` objects if the
# code expects them to be, hence `@patch("backend.app.api.routes_audio.UPLOAD_DIR", Path("/data/uploads"))`.
# The `Path.exists` mock is used in multiple places to control flow based on file/directory presence.
# The `FileResponse` mock for the download endpoint prevents issues with the test client trying to handle
# a real file stream response; instead, we check if `FileResponse` was called with correct arguments.`pytest` and `httpx` are in `backend/requirements.txt`, and `backend/tests/test_health.py` has been reviewed. `backend/tests/test_api_audio.py` has been created.

Now, I will create `backend/tests/test_service_audio.py`.

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

# --- New tests for actual file saving ---
import shutil
import uuid # For the mocked_uuid fixture
from backend.app.utils import storage as app_storage # To monkeypatch UPLOAD_DIR and DATA_ROOT
from backend.app.api import routes_audio as api_audio_module # To monkeypatch UPLOAD_DIR and DATA_ROOT used by the endpoint

# Define paths to test audio files, assuming tests run from project root
# Adjust if your test execution context is different.
PROJECT_ROOT_FROM_TEST_API_AUDIO = Path(__file__).resolve().parent.parent.parent 
TEST_FILES_DIR_FROM_TEST_API_AUDIO = PROJECT_ROOT_FROM_TEST_API_AUDIO / "test"
TEST_INTRO_OUTRO_MP3_FILE = TEST_FILES_DIR_FROM_TEST_API_AUDIO / "Intro_Outro_test.mp3"
TEST_MAIN_AUDIO_WAV_FILE = TEST_FILES_DIR_FROM_TEST_API_AUDIO / "Main_Audio_test.wav"
# Create a dummy text file for testing non-audio uploads
DUMMY_TEXT_FILE = TEST_FILES_DIR_FROM_TEST_API_AUDIO / "dummy.txt"
if not DUMMY_TEXT_FILE.parent.exists():
    DUMMY_TEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(DUMMY_TEXT_FILE, "w") as f:
    f.write("This is not an audio file.")


@pytest.fixture
def temp_dirs_for_upload_tests(tmp_path_factory, monkeypatch):
    """
    Fixture to set up temporary DATA_ROOT and UPLOAD_DIR for upload tests.
    UPLOAD_DIR will be <temp_data_root>/uploads.
    Yields (temp_data_root, temp_upload_dir).
    """
    temp_data_root_val = tmp_path_factory.mktemp("test_data_root")
    temp_upload_subdir_val = temp_data_root_val / "uploads" # as per original structure assumption
    temp_upload_subdir_val.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(app_storage, 'DATA_ROOT', temp_data_root_val)
    monkeypatch.setattr(app_storage, 'UPLOAD_DIR', temp_upload_subdir_val)
    
    monkeypatch.setattr(api_audio_module, 'DATA_ROOT', temp_data_root_val)
    monkeypatch.setattr(api_audio_module, 'UPLOAD_DIR', temp_upload_subdir_val)
        
    yield temp_data_root_val, temp_upload_subdir_val
    
    # Cleanup is handled by tmp_path_factory, but explicit removal can be added if needed for safety
    # For example, if ensure_dir_exists created other non-standard dirs not under tmp_path_factory control.
    # shutil.rmtree(temp_data_root_val, ignore_errors=True)


@pytest.fixture
def mocked_uuid_value_for_tests():
    # Generate a unique but predictable-format UUID for a test session
    return "test-session-uuid-" + str(uuid.uuid4())


@pytest.fixture
def mock_uuid_in_routes_audio(mocked_uuid_value_for_tests, monkeypatch):
    """Mocks uuid.uuid4() within the routes_audio module."""
    # Patching where uuid is *used*. Assuming it's `backend.app.api.routes_audio.uuid.uuid4`
    # If uuid is imported as `import uuid` then `uuid.uuid4` is correct.
    # If `from uuid import uuid4` then patch `backend.app.api.routes_audio.uuid4`.
    # Based on routes_audio.py, it's `import uuid`.
    monkeypatch.setattr(api_audio_module.uuid, 'uuid4', lambda: mocked_uuid_value_for_tests)
    return mocked_uuid_value_for_tests


@pytest.mark.asyncio
async def test_upload_main_track_wav_actually_saves(client: AsyncClient, temp_dirs_for_upload_tests, mock_uuid_in_routes_audio):
    _, temp_upload_dir = temp_dirs_for_upload_tests
    session_id = mock_uuid_in_routes_audio

    assert TEST_MAIN_AUDIO_WAV_FILE.exists(), f"Test file not found: {TEST_MAIN_AUDIO_WAV_FILE}"

    with open(TEST_MAIN_AUDIO_WAV_FILE, "rb") as f_wav:
        files = {"main_track": (TEST_MAIN_AUDIO_WAV_FILE.name, f_wav, "audio/wav")}
        response = await client.post("/api/audio/upload", files=files)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["upload_session_id"] == session_id
    assert "main_track" in data["saved_files"]
    
    # Path in response is relative to DATA_ROOT, should be "uploads/<session_id>/filename"
    expected_path_in_response = f"uploads/{session_id}/{TEST_MAIN_AUDIO_WAV_FILE.name}"
    assert data["saved_files"]["main_track"] == expected_path_in_response
    
    expected_file_on_disk = temp_upload_dir / session_id / TEST_MAIN_AUDIO_WAV_FILE.name
    assert expected_file_on_disk.exists()
    assert expected_file_on_disk.is_file()
    assert expected_file_on_disk.stat().st_size > 0


@pytest.mark.asyncio
async def test_upload_all_tracks_actually_saves(client: AsyncClient, temp_dirs_for_upload_tests, mock_uuid_in_routes_audio):
    _, temp_upload_dir = temp_dirs_for_upload_tests
    session_id = mock_uuid_in_routes_audio

    assert TEST_MAIN_AUDIO_WAV_FILE.exists()
    assert TEST_INTRO_OUTRO_MP3_FILE.exists()

    # For outro, let's use a different name to ensure paths are distinct in response
    outro_file_name = "Outro_test_copy.mp3"

    with open(TEST_MAIN_AUDIO_WAV_FILE, "rb") as f_main, \
         open(TEST_INTRO_OUTRO_MP3_FILE, "rb") as f_intro, \
         open(TEST_INTRO_OUTRO_MP3_FILE, "rb") as f_outro_orig: # Use original for content
        
        files = {
            "main_track": (TEST_MAIN_AUDIO_WAV_FILE.name, f_main, "audio/wav"),
            "intro": (TEST_INTRO_OUTRO_MP3_FILE.name, f_intro, "audio/mpeg"),
            "outro": (outro_file_name, f_outro_orig, "audio/mpeg"), 
        }
        response = await client.post("/api/audio/upload", files=files)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["upload_session_id"] == session_id
    assert "main_track" in data["saved_files"]
    assert "intro" in data["saved_files"]
    assert "outro" in data["saved_files"]

    expected_main_path_in_response = f"uploads/{session_id}/{TEST_MAIN_AUDIO_WAV_FILE.name}"
    expected_intro_path_in_response = f"uploads/{session_id}/{TEST_INTRO_OUTRO_MP3_FILE.name}"
    expected_outro_path_in_response = f"uploads/{session_id}/{outro_file_name}"

    assert data["saved_files"]["main_track"] == expected_main_path_in_response
    assert data["saved_files"]["intro"] == expected_intro_path_in_response
    assert data["saved_files"]["outro"] == expected_outro_path_in_response

    assert (temp_upload_dir / session_id / TEST_MAIN_AUDIO_WAV_FILE.name).exists()
    assert (temp_upload_dir / session_id / TEST_INTRO_OUTRO_MP3_FILE.name).exists()
    assert (temp_upload_dir / session_id / outro_file_name).exists()


@pytest.mark.asyncio
async def test_upload_no_main_track_does_not_save(client: AsyncClient, temp_dirs_for_upload_tests, mock_uuid_in_routes_audio):
    temp_data_root, temp_upload_dir = temp_dirs_for_upload_tests
    session_id = mock_uuid_in_routes_audio # uuid might still be generated before validation

    assert TEST_INTRO_OUTRO_MP3_FILE.exists()

    with open(TEST_INTRO_OUTRO_MP3_FILE, "rb") as f_intro:
        files = {"intro": (TEST_INTRO_OUTRO_MP3_FILE.name, f_intro, "audio/mpeg")}
        response = await client.post("/api/audio/upload", files=files)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    # Check that the session directory was not created, or if it was, it's empty.
    # The current save_uploaded_file calls ensure_dir_exists *before* writing.
    # And uuid is generated before any file operation.
    # So the directory might be created. The critical part is no *files* are saved.
    session_specific_upload_dir = temp_upload_dir / session_id
    if session_specific_upload_dir.exists():
        # Check if it's empty or contains no files relevant to this failed upload
        # For this test, we'll be strict: if it created the dir, it should be empty.
        # However, ensure_dir_exists is called inside save_uploaded_file, which is itself called per file.
        # Since main_track is missing, save_uploaded_file for main_track is never called.
        # If intro/outro were processed *before* main_track validation (not the case here), then their dirs might exist.
        # Given FastAPI validation happens before route code for missing required form fields,
        # save_uploaded_file might not even be called.
        # Let's assume the session_id directory might not even be created if validation fails early.
        # If it is created, it should not contain any of the "uploaded" files.
        # For a 422 due to missing main_track, the endpoint code that calls save_uploaded_file is not even reached for main_track.
        # And since main_track is the first one processed, no files should be saved.
        
        # Let's verify no files from this request are in the potential session directory
        # (though the directory itself might not exist if FastAPI validation is early enough)
        file_paths_to_check = [
             session_specific_upload_dir / TEST_INTRO_OUTRO_MP3_FILE.name
        ]
        for p in file_paths_to_check:
            assert not p.exists(), f"File {p} should not have been saved on 422 error."
    # A stronger check could be that session_specific_upload_dir itself doesn't exist,
    # but that depends on whether uuid generation and initial dir creation happen before FastAPI's form validation.
    # For form field validation (like missing main_track), FastAPI usually stops before route code runs.

@pytest.mark.asyncio
async def test_upload_saves_unknown_file_type_as_is(client: AsyncClient, temp_dirs_for_upload_tests, mock_uuid_in_routes_audio):
    """Tests that the endpoint saves a file even if it's not a typical audio format."""
    _, temp_upload_dir = temp_dirs_for_upload_tests
    session_id = mock_uuid_in_routes_audio

    assert DUMMY_TEXT_FILE.exists(), f"Test file not found: {DUMMY_TEXT_FILE}"

    with open(DUMMY_TEXT_FILE, "rb") as f_dummy: # rb mode for consistency with how UploadFile expects binary
        files = {"main_track": (DUMMY_TEXT_FILE.name, f_dummy, "text/plain")}
        response = await client.post("/api/audio/upload", files=files)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["upload_session_id"] == session_id
    assert "main_track" in data["saved_files"]
    
    expected_path_in_response = f"uploads/{session_id}/{DUMMY_TEXT_FILE.name}"
    assert data["saved_files"]["main_track"] == expected_path_in_response
    
    expected_file_on_disk = temp_upload_dir / session_id / DUMMY_TEXT_FILE.name
    assert expected_file_on_disk.exists()
    assert expected_file_on_disk.is_file()
    # Verify content if desired, e.g. by reading it back
    assert expected_file_on_disk.read_bytes() == DUMMY_TEXT_FILE.read_bytes()


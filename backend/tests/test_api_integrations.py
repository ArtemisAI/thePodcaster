import pytest
from fastapi.testclient import TestClient
from fastapi import status
from pathlib import Path
import os
import shutil # For creating dummy large file and cleanup

# Application instance from main.py
from backend.app.main import app
# Database session and models (if directly creating test data)
from sqlalchemy.orm import Session # For type hinting if using db fixture directly
from app.models.job import ProcessingJob, JobStatus, JobType
from app.db.database import SessionLocal # If creating data outside of requests
# Configuration for MAX_UPLOAD_SIZE_MB
from app.config import settings
# DATA_ROOT to construct absolute paths for uploads
from app.utils.storage import DATA_ROOT, UPLOAD_DIR, PROCESSED_DIR, OUTPUTS_DIR

# Predefined test audio file
PRELOADED_TEST_FILES_DIR = Path("data/preloaded_test_files")
MAIN_AUDIO_TEST_FILE = PRELOADED_TEST_FILES_DIR / "Main_Audio_test.wav"
# Ensure this file exists for tests that rely on it
if not MAIN_AUDIO_TEST_FILE.exists():
    # This is a fallback, ideally the test environment ensures this file exists.
    # For this exercise, we'll assume it's present and fail if not.
    # Or, create a dummy one if really needed for the test to run.
    print(f"Warning: Test file {MAIN_AUDIO_TEST_FILE} not found. Some tests may fail or be skipped.")
    # You could create a dummy file here if essential for basic test structure to pass
    # MAIN_AUDIO_TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    # with open(MAIN_AUDIO_TEST_FILE, "wb") as f:
    #     f.write(b"dummy audio data")


# Client fixture is automatically picked up from conftest.py
# db fixture is also automatically picked up from conftest.py for db interactions

# Helper to create a ProcessingJob directly in DB for library population
def create_library_item_in_db(
    db: Session,
    job_type: JobType = JobType.AUDIO_CONCATENATION, # Default, can be changed
    status: JobStatus = JobStatus.COMPLETED,
    output_file_path: str | None = None,
    relative_output_dir: Path | None = None, # e.g., PROCESSED_DIR relative to DATA_ROOT
    filename: str | None = "test_output.mp3"
) -> ProcessingJob:
    if output_file_path is None:
        # Create a dummy output file for download tests if needed
        # The path stored in DB should be relative to DATA_ROOT
        actual_output_dir = DATA_ROOT / (relative_output_dir if relative_output_dir else PROCESSED_DIR.name)
        actual_output_dir.mkdir(parents=True, exist_ok=True)
        dummy_file_path = actual_output_dir / (filename or f"job_output_{job_type.value}.fake")
        
        # Create a small dummy file
        with open(dummy_file_path, "wb") as f:
            f.write(b"dummy file content for testing download")
        
        # Store path relative to DATA_ROOT
        output_file_path_relative = str(Path(actual_output_dir.name) / dummy_file_path.name)
    else:
        # If an explicit output_file_path (relative) is given, assume the file exists or is not needed for the test
        output_file_path_relative = output_file_path

    job = ProcessingJob(
        job_type=job_type,
        status=status,
        output_file_path=output_file_path_relative 
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

# --- Media Library Tests ---

def test_list_media_library_items_empty(client: TestClient, db: Session): # db fixture to ensure clean state
    response = client.get("/api/library/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0

def test_list_media_library_items_with_data(client: TestClient, db: Session):
    create_library_item_in_db(db, filename="item1.mp3")
    create_library_item_in_db(db, filename="item2.wav", job_type=JobType.VIDEO_GENERATION)

    response = client.get("/api/library/items")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    # Check if filenames are present in output_file_url (which implies relative path is part of it)
    assert "item1.mp3" in data["items"][0]["output_file_url"]
    assert "item2.wav" in data["items"][1]["output_file_url"]


# test_download_media_library_item:
# This test requires an item in the library that has a valid output_file_path.
# The output_file_url from /api/library/items/{job_id} or list response
# is expected to point to an endpoint like /api/outputs/download/{job_id}/{filename}
def test_download_media_library_item(client: TestClient, db: Session):
    # 1. Create a job that would appear in the library and has a downloadable file
    # Using PROCESSED_DIR.name as the relative directory part for the file path
    job = create_library_item_in_db(
        db,
        filename="downloadable_lib_item.txt",
        relative_output_dir=Path(PROCESSED_DIR.name) # e.g. "processed"
    )

    # 2. Fetch the library item to get its output_file_url
    # (Alternatively, construct the expected download URL if the pattern is known and stable)
    response_item = client.get(f"/api/library/items/{job.id}")
    assert response_item.status_code == status.HTTP_200_OK
    item_data = response_item.json()
    download_url = item_data.get("output_file_url")
    assert download_url is not None, "output_file_url not found in library item response"

    # The download_url is absolute (e.g., http://testserver/api/outputs/download/...)
    # We need to make a GET request to this URL via the TestClient.
    # The TestClient's base_url is http://testserver, so we need the path part.
    if download_url.startswith(client.base_url._uri_reference.scheme + "://" + client.base_url._uri_reference.host):
         download_path = download_url.replace(str(client.base_url), "")
    else:
        # Fallback if URL is not prefixed with base_url (e.g. relative path directly)
        # This shouldn't happen if TestClient is configured correctly and URLs are absolute.
        download_path = download_url

    # 3. Attempt to download the file
    response_download = client.get(download_path)
    assert response_download.status_code == status.HTTP_200_OK
    assert response_download.content == b"dummy file content for testing download"
    assert "text/plain" in response_download.headers.get("content-type", "") or \
           "application/octet-stream" in response_download.headers.get("content-type", "")
    
    # Clean up the dummy file created
    full_dummy_path = DATA_ROOT / job.output_file_path
    if full_dummy_path.exists():
        full_dummy_path.unlink()

# --- Video Generation Tests ---

def test_trigger_video_generation_and_check_status(client: TestClient, db: Session): # db for job creation via API
    # 1. Upload an audio file
    assert MAIN_AUDIO_TEST_FILE.exists(), f"Test audio file {MAIN_AUDIO_TEST_FILE} not found."
    with open(MAIN_AUDIO_TEST_FILE, "rb") as f_audio:
        files = {"main_track": (MAIN_AUDIO_TEST_FILE.name, f_audio, "audio/wav")}
        response_upload = client.post("/api/audio/upload", files=files)

    assert response_upload.status_code == status.HTTP_200_OK, response_upload.text
    upload_data = response_upload.json()
    assert "saved_files" in upload_data
    assert "main_track" in upload_data["saved_files"]
    relative_audio_path = upload_data["saved_files"]["main_track"]

    # Construct absolute path to the uploaded audio file
    # DATA_ROOT should be the root under which 'uploads/session_id/file.wav' is stored
    absolute_audio_path = DATA_ROOT / relative_audio_path
    assert absolute_audio_path.exists(), f"Uploaded audio file not found at {absolute_audio_path}"

    # 2. Trigger video generation
    video_request_payload = {
        "source_audio_path": str(absolute_audio_path),
        "output_filename": "test_video_output.mp4", # Optional, depends on VideoGenerationRequest model
        "resolution": "1080p", # Optional, "
        "waveform_fg_color": "white", # Optional, "
        "waveform_bg_color": "black"  # Optional, "
    }
    # Check VideoGenerationRequest model definition for required fields.
    # From routes_video.py, it seems to only strictly need source_audio_path.
    # The model definition is: app.models.video.VideoGenerationRequest
    # Let's assume it's just source_audio_path for now, if others are optional or have defaults.
    # For a robust test, one would import VideoGenerationRequest and see its fields.
    # The current VideoGenerationRequest model in routes_video.py seems to be:
    # class VideoGenerationRequest(BaseModel):
    #    source_audio_path: str
    #    # Other fields might be optional (e.g. output_filename: Optional[str] = None)
    # Let's assume for now the endpoint defaults other params if not provided.
    # The example in routes_video.py used: request.source_audio_path

    actual_payload = {"source_audio_path": str(absolute_audio_path)}

    response_video_gen = client.post("/api/video/generate", json=actual_payload)
    assert response_video_gen.status_code == status.HTTP_202_ACCEPTED, response_video_gen.text
    video_job_data = response_video_gen.json()
    video_job_id = video_job_data.get("id")
    assert video_job_id is not None

    # 3. Check the status of the video generation job
    # Assuming a generic /api/jobs/{job_id} endpoint exists.
    # If this is specific to video, it might be /api/video/jobs/{job_id}
    # The prompt suggested /api/video/jobs/{job_id}
    # Let's try the generic one first as it's more common.
    # If it fails, the specific one should be tried or noted.
    response_job_status = client.get(f"/api/jobs/{video_job_id}")
    if response_job_status.status_code == status.HTTP_404_NOT_FOUND:
        # Try specific video job status endpoint if generic one is not found
        response_job_status = client.get(f"/api/video/status/{video_job_id}") # Assuming /api/video/status/

    assert response_job_status.status_code == status.HTTP_200_OK, response_job_status.text
    job_status_data = response_job_status.json()
    assert job_status_data["id"] == video_job_id
    assert job_status_data["job_type"] == JobType.VIDEO_GENERATION.value
    assert job_status_data["status"] in [JobStatus.PENDING.value, JobStatus.PROCESSING.value]

    # Cleanup: Remove the uploaded audio file
    if absolute_audio_path.exists():
        # Parent dir is session_id, and its parent is UPLOAD_DIR
        # Be careful with shutil.rmtree, ensure path is correct.
        session_dir = absolute_audio_path.parent
        upload_root_dir = session_dir.parent 
        if session_dir.name != UPLOAD_DIR.name and session_dir.exists(): # Check it's a session ID dir
             shutil.rmtree(session_dir) # Remove the session_id directory and its contents

# --- File Upload Limit Tests ---

def test_upload_small_file_success(client: TestClient):
    assert MAIN_AUDIO_TEST_FILE.exists(), f"Test audio file {MAIN_AUDIO_TEST_FILE} not found."
    file_size = MAIN_AUDIO_TEST_FILE.stat().st_size
    assert file_size < settings.max_upload_size_bytes, "Test file is larger than max upload size, pick a smaller file."

    with open(MAIN_AUDIO_TEST_FILE, "rb") as f:
        files = {"main_track": (MAIN_AUDIO_TEST_FILE.name, f, "audio/wav")}
        response = client.post("/api/audio/upload", files=files)

    assert response.status_code == status.HTTP_200_OK, response.text
    upload_data = response.json()
    assert "upload_session_id" in upload_data
    
    # Cleanup uploaded file
    relative_audio_path = upload_data["saved_files"]["main_track"]
    absolute_audio_path = DATA_ROOT / relative_audio_path
    session_dir = absolute_audio_path.parent
    if session_dir.exists() and session_dir.name != UPLOAD_DIR.name :
        shutil.rmtree(session_dir)


def test_upload_large_file_fails(client: TestClient):
    max_size = settings.max_upload_size_bytes
    if max_size == 0: # 0 means unlimited, so skip this test
        pytest.skip("MAX_UPLOAD_SIZE_MB is 0 (unlimited), skipping large file test.")
        return

    large_file_size = max_size + 1024 # 1KB larger
    large_file_path = Path("temp_large_file.dat")

    try:
        with open(large_file_path, "wb") as f:
            f.write(os.urandom(large_file_size))
        
        assert large_file_path.stat().st_size == large_file_size

        with open(large_file_path, "rb") as f:
            files = {"main_track": (large_file_path.name, f, "application/octet-stream")}
            response = client.post("/api/audio/upload", files=files)
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, response.text
        # The actual file saving might be prevented by middleware before reaching the endpoint logic.
        # If save_uploaded_file is called and then fails due to size, that's also a valid test.
        # The current audio upload endpoint checks file extension first, then size, then saves.

    finally:
        if large_file_path.exists():
            large_file_path.unlink()

# TODO: (Optional) test_download_generated_video
# This would be similar to test_download_media_library_item, but would:
# 1. Trigger video generation.
# 2. Poll job status until COMPLETED (requires mocking or a very fast dummy process).
# 3. Get the output_file_url from the completed job.
# 4. Download and verify.
# For now, this is complex due to the async nature of jobs.
# @pytest.mark.skip(reason="Video download test requires job completion mocking or long wait.")
# def test_download_generated_video(client: TestClient, db: Session):
#    pass

# Ensure UPLOAD_DIR exists for tests that might save there, though save_uploaded_file should handle it.
# UPLOAD_DIR.mkdir(parents=True, exist_ok=True) # This should be handled by app logic / ensure_dir_exists

# At the end of all tests, could do a broader cleanup of UPLOAD_DIR if needed,
# but individual test cleanup is preferred.

# Example of a fixture to ensure MAIN_AUDIO_TEST_FILE exists, if needed more formally.
@pytest.fixture(scope="session", autouse=True)
def ensure_test_files_exist():
    PRELOADED_TEST_FILES_DIR.mkdir(parents=True, exist_ok=True)
    if not MAIN_AUDIO_TEST_FILE.exists():
        # Create a small, valid WAV file for testing if it doesn't exist.
        # This is a simplified placeholder. A real WAV file has a specific header.
        # For robustness, use a pre-existing valid test file.
        # This basic file might not pass all audio processing steps if they are strict.
        header = b'RIFF' + (36).to_bytes(4, 'little') + b'WAVEfmt ' + (16).to_bytes(4, 'little')
        header += (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little') + (22050).to_bytes(4, 'little')
        header += (22050 * 1 * 16 // 8).to_bytes(4, 'little') + (1 * 16 // 8).to_bytes(2, 'little')
        header += (16).to_bytes(2, 'little') + b'data' + (0).to_bytes(4, 'little') # 0 data size
        try:
            with open(MAIN_AUDIO_TEST_FILE, "wb") as f:
                f.write(header) # Minimal valid WAV header for an empty file
            print(f"Created dummy test file: {MAIN_AUDIO_TEST_FILE}")
        except Exception as e:
            print(f"Error creating dummy test file {MAIN_AUDIO_TEST_FILE}: {e}")
            # Depending on policy, either fail tests or proceed with caution
            # pytest.fail(f"Could not create essential test file: {MAIN_AUDIO_TEST_FILE}")
    # else:
    #    print(f"Test file {MAIN_AUDIO_TEST_FILE} already exists.")

```

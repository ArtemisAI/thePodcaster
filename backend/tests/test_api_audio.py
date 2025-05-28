import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, call, ANY
from pathlib import Path
from fastapi import HTTPException, status

# Assuming app is created via create_app() in main.py or similar for testing context
# If your main.py directly creates 'app = FastAPI()', this import is fine.
from backend.app.main import app
# If ALLOWED_EXTENSIONS is defined in routes_audio, better to import it to keep tests in sync
from backend.app.api.routes_audio import ALLOWED_EXTENSIONS


client = TestClient(app)


@patch("backend.app.api.routes_audio.save_uploaded_file")
def test_upload_audio_main_track_success(mock_save_file):
    mock_session_id = "mock_session_main_only"
    # Mock uuid.uuid4() to control session_id
    with patch("backend.app.api.routes_audio.uuid.uuid4", return_value=MagicMock(hex=mock_session_id, __str__=lambda: mock_session_id)):
        mock_save_file.return_value = Path(f"uploads/{mock_session_id}/test_main.mp3")
        
        files = {"main_track": ("test_main.mp3", b"some audio data", "audio/mpeg")}
        response = client.post("/api/audio/upload", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "upload_session_id" in data
        assert data["upload_session_id"] == mock_session_id
        assert "saved_files" in data
        assert "main_track" in data["saved_files"]
        assert data["saved_files"]["main_track"] == f"uploads/{mock_session_id}/test_main.mp3" # Path.relative_to(DATA_ROOT) is used in endpoint
        
        mock_save_file.assert_called_once()
        # Check that the first argument to save_uploaded_file (the UploadFile object) has the correct filename
        assert mock_save_file.call_args[0][0].filename == "test_main.mp3"
        # Check that the second argument (session_id) is correct
        assert mock_save_file.call_args[0][1] == mock_session_id


@patch("backend.app.api.routes_audio.save_uploaded_file")
def test_upload_audio_all_tracks_success(mock_save_file):
    mock_session_id = "mock_session_all_tracks"
    with patch("backend.app.api.routes_audio.uuid.uuid4", return_value=MagicMock(hex=mock_session_id, __str__=lambda: mock_session_id)):
        # Define different return values for each call
        mock_save_file.side_effect = [
            Path(f"uploads/{mock_session_id}/test_main.mp3"),
            Path(f"uploads/{mock_session_id}/test_intro.mp3"),
            Path(f"uploads/{mock_session_id}/test_outro.mp3"),
        ]
        
        files = {
            "main_track": ("test_main.mp3", b"main audio", "audio/mpeg"),
            "intro": ("test_intro.mp3", b"intro audio", "audio/mpeg"),
            "outro": ("test_outro.mp3", b"outro audio", "audio/mpeg"),
        }
        response = client.post("/api/audio/upload", files=files)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "upload_session_id" in data
        assert data["upload_session_id"] == mock_session_id
        assert "saved_files" in data
        assert data["saved_files"]["main_track"] == f"uploads/{mock_session_id}/test_main.mp3"
        assert data["saved_files"]["intro"] == f"uploads/{mock_session_id}/test_intro.mp3"
        assert data["saved_files"]["outro"] == f"uploads/{mock_session_id}/test_outro.mp3"
        
        assert mock_save_file.call_count == 3
        
        # Check calls were made with correct filenames and session_id
        called_filenames_with_session = {(args[0].filename, args[1]) for args, _ in mock_save_file.call_args_list}
        expected_filenames_with_session = {
            ("test_main.mp3", mock_session_id),
            ("test_intro.mp3", mock_session_id),
            ("test_outro.mp3", mock_session_id)
        }
        assert called_filenames_with_session == expected_filenames_with_session


@patch("backend.app.api.routes_audio.save_uploaded_file") # Keep patch even if not called for consistency
def test_upload_audio_disallowed_extension_main_track(mock_save_file):
    files = {"main_track": ("test_main.txt", b"some text data", "text/plain")}
    response = client.post("/api/audio/upload", files=files)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data
    assert "unsupported extension" in data["detail"].lower()
    assert "'.txt'" in data["detail"] 
    assert "test_main.txt" in data["detail"]
    assert Path("test_main.txt").suffix.lower() not in ALLOWED_EXTENSIONS
    mock_save_file.assert_not_called()


@patch("backend.app.api.routes_audio.save_uploaded_file")
def test_upload_audio_disallowed_extension_optional_track(mock_save_file):
    # Main track is fine, intro is not. Validation should prevent any saves.
    files = {
        "main_track": ("test_main.mp3", b"main audio", "audio/mpeg"),
        "intro": ("test_intro.txt", b"intro text", "text/plain"),
    }
    response = client.post("/api/audio/upload", files=files)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data
    assert "unsupported extension" in data["detail"].lower()
    assert "'test_intro.txt'" in data["detail"]
    mock_save_file.assert_not_called() # Validation happens before any save attempt


@patch("backend.app.api.routes_audio.save_uploaded_file")
def test_upload_audio_save_fails_on_main_track(mock_save_file):
    mock_session_id = "mock_session_fail_main"
    with patch("backend.app.api.routes_audio.uuid.uuid4", return_value=MagicMock(hex=mock_session_id, __str__=lambda: mock_session_id)):
        # Simulate save_uploaded_file raising an Exception (like IOError)
        mock_save_file.side_effect = Exception("Simulated disk full") 
        
        files = {"main_track": ("test_main.mp3", b"some audio data", "audio/mpeg")}
        response = client.post("/api/audio/upload", files=files)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "error saving file: test_main.mp3" in data["detail"].lower()
        assert "simulated disk full" in data["detail"].lower() 
        
        mock_save_file.assert_called_once()
        assert mock_save_file.call_args[0][0].filename == "test_main.mp3"
        assert mock_save_file.call_args[0][1] == mock_session_id


@patch("backend.app.api.routes_audio.save_uploaded_file")
def test_upload_audio_save_fails_on_optional_track(mock_save_file):
    mock_session_id = "mock_session_fail_optional"
    with patch("backend.app.api.routes_audio.uuid.uuid4", return_value=MagicMock(hex=mock_session_id, __str__=lambda: mock_session_id)):
        
        def side_effect_func(upload_file, session_id_str):
            assert session_id_str == mock_session_id # Ensure session_id is consistent
            if upload_file.filename == "test_main.mp3":
                return Path(f"uploads/{session_id_str}/{upload_file.filename}")
            elif upload_file.filename == "test_intro.mp3":
                raise Exception("Simulated intro save error") 
            pytest.fail(f"Unexpected call to save_uploaded_file with {upload_file.filename}")

        mock_save_file.side_effect = side_effect_func
        
        files = {
            "main_track": ("test_main.mp3", b"main audio", "audio/mpeg"),
            "intro": ("test_intro.mp3", b"intro audio", "audio/mpeg"), 
        }
        response = client.post("/api/audio/upload", files=files)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "error saving file: test_intro.mp3" in data["detail"].lower()
        assert "simulated intro save error" in data["detail"].lower()
        
        assert mock_save_file.call_count == 2
        
        call_args_list = mock_save_file.call_args_list
        assert call_args_list[0][0][0].filename == "test_main.mp3"
        assert call_args_list[0][0][1] == mock_session_id
        
        assert call_args_list[1][0][0].filename == "test_intro.mp3"
        assert call_args_list[1][0][1] == mock_session_id

# Test for filename missing on an optional track (if provided)
@patch("backend.app.api.routes_audio.save_uploaded_file")
def test_upload_optional_track_no_filename(mock_save_file):
    mock_session_id = "mock_session_no_filename"
    with patch("backend.app.api.routes_audio.uuid.uuid4", return_value=MagicMock(hex=mock_session_id, __str__=lambda: mock_session_id)):
        # Main track is okay for this test's purpose before validation fails for intro
        # However, the current code validates all files first.
        
        # Create an UploadFile mock that has a None filename
        intro_file_mock = MagicMock()
        intro_file_mock.filename = None # Explicitly set filename to None
        # These might not be strictly necessary if the code only checks filename
        intro_file_mock.file = b"some intro data" 
        intro_file_mock.content_type = "audio/mpeg"

        files = {
            "main_track": ("test_main.mp3", b"main audio", "audio/mpeg"),
            "intro": intro_file_mock 
        }
                
        response = client.post("/api/audio/upload", files=files)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "intro file is invalid (no filename)" in data["detail"].lower()
        
        mock_save_file.assert_not_called() # Validation fails before any save attempt

# Test for filename missing on the required main_track
@patch("backend.app.api.routes_audio.save_uploaded_file")
def test_upload_main_track_no_filename(mock_save_file):
    main_file_mock = MagicMock()
    main_file_mock.filename = None
    main_file_mock.file = b"some main data"
    main_file_mock.content_type = "audio/mpeg"

    files = {"main_track": main_file_mock}
    
    response = client.post("/api/audio/upload", files=files)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data
    assert "main track file is invalid (no filename)" in data["detail"].lower()
    mock_save_file.assert_not_called()

```

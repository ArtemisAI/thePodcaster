from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)


def create_session(tmp_path: Path, name: str, files: list[str]):
    session_dir = tmp_path / name
    session_dir.mkdir()
    for f in files:
        (session_dir / f).write_text("data")


def test_list_upload_sessions(tmp_path: Path):
    create_session(tmp_path, "s1", ["a.mp3"])
    create_session(tmp_path, "s2", [])
    with patch("app.api.routes_audio.UPLOAD_DIR", tmp_path):
        resp = client.get("/api/audio/uploads")
        assert resp.status_code == 200
        assert set(resp.json()) == {"s1", "s2"}


def test_list_files_in_session(tmp_path: Path):
    create_session(tmp_path, "session123", ["foo.mp3", "bar.wav"])
    with patch("app.api.routes_audio.UPLOAD_DIR", tmp_path):
        resp = client.get("/api/audio/uploads/session123")
        assert resp.status_code == 200
        assert set(resp.json()) == {"foo.mp3", "bar.wav"}

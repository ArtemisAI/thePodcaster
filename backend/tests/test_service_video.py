import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY
import ffmpeg

from backend.app.services.video_processing import generate_waveform_video


@pytest.fixture
def temp_audio_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "input.mp3"
    file_path.write_text("dummy")
    return file_path


@pytest.fixture
def mock_ffmpeg_methods():
    with patch("ffmpeg.input") as mock_input, \
         patch("ffmpeg.overlay") as mock_overlay, \
         patch("ffmpeg.output") as mock_output, \
         patch("ffmpeg.run") as mock_run:
        mock_stream = MagicMock()
        mock_input.return_value = mock_stream
        mock_overlay.return_value = mock_stream
        mock_output.return_value = mock_stream
        yield {
            "input": mock_input,
            "overlay": mock_overlay,
            "output": mock_output,
            "run": mock_run,
            "stream": mock_stream,
        }


def test_generate_waveform_video_success(mock_ffmpeg_methods, temp_audio_file: Path, tmp_path: Path):
    output = tmp_path / "out.mp4"
    result = generate_waveform_video(temp_audio_file, output, "640x360", "white", "black")

    assert result == output
    mock_ffmpeg_methods["input"].assert_any_call(str(temp_audio_file))
    mock_ffmpeg_methods["output"].assert_called_once_with(mock_ffmpeg_methods["overlay"].return_value, str(output), vcodec="libx264", pix_fmt="yuv420p")
    mock_ffmpeg_methods["run"].assert_called_once()


def test_generate_waveform_video_file_not_found(tmp_path: Path):
    input_path = tmp_path / "missing.mp3"
    output = tmp_path / "out.mp4"
    with pytest.raises(FileNotFoundError):
        generate_waveform_video(input_path, output, "640x360", "white", "black")


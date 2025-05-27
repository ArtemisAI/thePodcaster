"""Video processing helpers (waveform generation)."""
from pathlib import Path

def generate_waveform_video(
    audio_input_path: Path,
    video_output_path: Path,
    resolution: str,
    fg_color: str,
    bg_color: str,
    background_image_path: Path | None = None,
) -> Path:
    """
    Stub for waveform video generation.

    Raises:
        NotImplementedError: Always, as video generation is not implemented.
    """
    raise NotImplementedError("Video generation not implemented.")
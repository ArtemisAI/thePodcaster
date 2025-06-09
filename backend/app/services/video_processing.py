"""Video processing helpers (waveform generation)."""

from __future__ import annotations

from pathlib import Path
import logging
import ffmpeg

from app.utils.storage import ensure_dir_exists
from app.config import settings

logger = logging.getLogger(__name__)


def generate_waveform_video(
    audio_input_path: Path,
    video_output_path: Path,
    resolution: str,
    fg_color: str,
    bg_color: str,
    background_image_path: Path | None = None,
) -> Path:
    """Generate a simple waveform video using FFmpeg."""

    if not audio_input_path.exists():
        logger.error("Audio input %s not found", audio_input_path)
        raise FileNotFoundError(f"Audio input not found: {audio_input_path}")

    ensure_dir_exists(video_output_path.parent)

    try:
        audio_stream = ffmpeg.input(str(audio_input_path))

        wave = audio_stream.filter(
            "showwavespic", s=resolution, colors=fg_color
        )

        if background_image_path:
            background = ffmpeg.input(str(background_image_path))
        else:
            background = ffmpeg.input(
                f"color=c={bg_color}:s={resolution}", f="lavfi"
            )

        overlaid = ffmpeg.overlay(background, wave)

        video_stream = ffmpeg.output(
            overlaid,
            str(video_output_path),
            vcodec="libx264",
            pix_fmt="yuv420p",
        )

        ffmpeg.run(
            video_stream,
            cmd=getattr(settings, "FFMPEG_PATH", "ffmpeg"),
            overwrite_output=True,
            capture_stdout=True,
            capture_stderr=True,
        )
    except ffmpeg.Error as exc:
        stderr = exc.stderr.decode("utf8") if exc.stderr else str(exc)
        logger.error("FFmpeg error generating video: %s", stderr)
        raise
    return video_output_path

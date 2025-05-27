"""Filesystem & object storage helpers."""

import os
from pathlib import Path

# Determine base data directory:
# 1. Use DATA_ROOT env var if set.
# 2. Else, if /data exists, assume Docker environment and use /data.
# 3. Otherwise, use project_root/data (development environment).
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_DATA_ROOT = os.getenv("DATA_ROOT")
if _ENV_DATA_ROOT:
    DATA_ROOT = Path(_ENV_DATA_ROOT)
elif Path("/data").exists():
    DATA_ROOT = Path("/data")
else:
    DATA_ROOT = _PROJECT_ROOT / "data"

# Directories for uploads, processed files, and transcripts
UPLOAD_DIR = DATA_ROOT / "uploads"
PROCESSED_DIR = DATA_ROOT / "processed"
TRANSCRIPT_DIR = DATA_ROOT / "transcripts"

def ensure_dir_exists(path: Path) -> Path:
    """Ensure that the given directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path

def save_transcript_to_files(
    output_basename: str,
    plain_text: str,
    srt_text: str,
    transcript_dir: Path,
) -> tuple[Path, Path]:
    """
    Save transcripts in plain text and SRT formats under the transcript directory.

    Returns:
        Tuple of (relative_txt_path, relative_srt_path) relative to DATA_ROOT.
    """
    ensure_dir_exists(transcript_dir)
    txt_path = transcript_dir / f"{output_basename}.txt"
    srt_path = transcript_dir / f"{output_basename}.srt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_text)
    return txt_path.relative_to(DATA_ROOT), srt_path.relative_to(DATA_ROOT)

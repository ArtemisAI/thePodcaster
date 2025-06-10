"""Thin wrapper around the ``ffmpeg`` CLI ensuring safe argument handling."""

from __future__ import annotations

import subprocess
from subprocess import CalledProcessError, CompletedProcess

from ..config import settings


def run_ffmpeg(*args: str) -> CompletedProcess:
    """Execute ``ffmpeg`` with the given arguments.

    Parameters
    ----------
    *args:
        Arguments passed directly to ``ffmpeg``.

    Returns
    -------
    subprocess.CompletedProcess
        The result object containing stdout and stderr.
    """

    ffmpeg_bin = getattr(settings, "FFMPEG_PATH", "ffmpeg")
    cmd = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", *args]

    try:
        return subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except CalledProcessError as exc:  # pragma: no cover - thin wrapper
        exc.cmd = " ".join(cmd)
        raise


# -----------------------------------------------------------------------------
# Backend Dockerfile – FastAPI + Celery + FFmpeg + Whisper
# -----------------------------------------------------------------------------
# The image is purposely split into two stages:
#   1. builder: install Python dependencies + FFmpeg + Whisper models
#   2. runtime: slimmer layer to keep container size low
#
# NOTE: All dependency versions should ultimately be pinned inside a
# requirements.txt or pyproject.toml file. For the scaffolding phase we simply
# outline the commands that *will* be necessary.
# -----------------------------------------------------------------------------

FROM python:3.11-slim AS base

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (for cache)
WORKDIR /code

# Placeholder: add your dependency manager of choice (pip/poetry/pipenv)
# For now we copy an empty requirements.txt so the file exists
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy actual source later – this will be mounted in dev mode anyway
COPY . /code

# Default command – can be overridden in compose
CMD ["bash"]

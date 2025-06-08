# ROADMAP – Rebuilding The Podcaster

This repository stores the archived implementation under the `OUT/` directory. The plan below defines how to rebuild the project incrementally, validating each slice with automated tests and continuous integration.

## Milestone 1 – Repository bootstrap & CI
- Create base folders: `backend`, `frontend`, `docs`, `tests`.
- Add Dockerfile for a minimal FastAPI backend.
- Compose stack with Postgres and Redis.
- Configure pre-commit hooks (black, isort, flake8, mypy).
- GitHub Actions pipeline running lint and unit tests.
- Implement `/api/health` route to verify the stack.

**Deliverable:** `docker compose up` returns HTTP 200 on `/api/health`.

## Milestone 2 – Audio ingestion & processing
- Endpoint `POST /audio/upload` accepting intro, main and outro files.
- Save uploads to `/data/uploads/<session>/`.
- Celery task `merge_tracks` normalises and merges audio with FFmpeg.
- Persist job status in Postgres via `ProcessingJob` model.
- APIs to list sessions and download originals or processed files.
- Unit tests for upload limits and task success paths.

**Deliverable:** User can upload segments and receive processed audio; tests cover the API and Celery tasks.

## Milestone 3 – Waveform video exporter
- Celery task `generate_waveform_video` using FFmpeg `showwaves`.
- Parameters for colour, resolution and background image.
- Endpoint `/video/{id}` to download the resulting video.

**Deliverable:** MP4 video rendered from processed audio.

## Milestone 4 – Transcription service
- Bundle Faster‑Whisper in the backend image.
- Async task `transcribe_audio` returning SRT and plain text.
- Store transcripts in Postgres and the filesystem.

## Milestone 5 – LLM suggestions
- Add Ollama container and `/ai/suggest` endpoint.
- Persist AI suggestions for episode titles and summaries.

## Milestone 6 – Publishing automation
- Integrate n8n for external workflow automation.
- Trigger a webhook when processing jobs complete.

## Milestone 7 – Frontend evolution
- Begin with a simple HTML/JS interface for uploads and job lists.
- Gradually migrate to React + Vite with TypeScript.
- Add end‑to‑end tests for the upload and processing flow.

## Stretch Goals
- WebSocket progress updates and user preferences for video export.
- Multi-user authentication and cloud export profiles.
- Subtitle burn‑in for generated videos.

### Development Principles
- Keep pull requests small and focused with updated docs and types first.
- Fail fast: explicit logging and error handling should surface issues early.
- Every feature includes automated tests before merging.

For historical context, the previous roadmap and source code remain in the `OUT/` directory.

# Roadmap – The Podcaster

_Note: A `features` branch has been created, integrating several completed functionalities and fixes. New integration tests have also been added to verify these core features._

This file expands the high-level milestones listed in the README into concrete, actionable tasks.  Each task contains an ID that we will reference in issues and PR titles (e.g. `#A2`).

---

## Milestone 1 – Repository bootstrap & CI (week 1)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|A1|Create base folder structure (backend, frontend, docs, …)|0.5d|Done by scaffolding agent|
|A2|Write basic Dockerfile for backend (FastAPI + poetry/pip)|0.5d|Healthcheck route only|
|A3|Draft docker-compose stack incl. Postgres & Redis|0.5d|Compose v3 syntax|
|A4|Add pre-commit config (black, isort, flake8, mypy)|0.5d|CI will run hooks|
|A5|Set-up GitHub Actions CI pipeline|0.5d|Test & lint stages|

Deliverable: `docker compose up` results in a running FastAPI container returning HTTP 200 on `/api/health`.

---

## Milestone 2 – Audio ingestion & processing (week 2-3)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|B1|POST `/audio/upload` endpoint with multipart support|1d|Status: Implemented. Files saved to session-specific dirs. APIs for listing sessions, files within sessions, downloading originals, and deleting sessions now exist. **2025-05-30**: Fixed Nginx proxy configuration that caused `502` on `/api/audio/upload`. This is part of the `features` branch integration.|
|B2|Define Celery tasks for `merge_tracks`, `normalize_volume`, etc.|1d|FFmpeg wrapper|
|B3|Persist job status in Postgres (SQLModel)|0.5d|Status: Implemented. `ProcessingJob` model used. APIs for listing/deleting processed files (job outputs) exist. The new Media Library API (`/api/library`) provides enhanced, paginated access to completed jobs and their related artifacts (transcripts, LLM suggestions). This is part of the `features` branch integration.|
|B4|Send progress updates over WebSocket (FastAPI)|1d|Planned. See `docs/websocket_integration_plan.md` for detailed strategy.|
|B5|Enhanced File Management APIs|N/A|Implemented. Includes: listing upload sessions, files within sessions; downloading original uploaded files; deleting upload sessions; listing processed/completed job outputs; deleting processed job outputs; managing a separate 'outputs' directory with list, download, delete APIs. Complemented by the new Media Library API for browsing final outputs.|
|B6|Robust Logging and Startup Checks|N/A|Implemented. Logging to `backend/logs/app.log` with rotation. Startup checks for existence and writability of uploads, processed, outputs, and log directories.|
|B7|Configurable per-file upload size limit & graceful 413 errors|N/A|Status: Implemented. Configurable via `MAX_UPLOAD_SIZE_MB` (see `config.py`, Docker & Nginx settings). Graceful 413 errors handled. This is part of the `features` branch integration.|

Deliverable: user can upload intro, episode, outro; backend returns processed WAV/MP3.

---

## Milestone 3 – Waveform video exporter (week 3-4)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|C1|Implement `generate_waveform_video` Celery task|1d|Status: Implemented. API endpoint for triggering video generation (`POST /api/video/generate`) is available on the `features` branch. The Celery task implementation itself is a placeholder within the API, actual video processing logic in the task is pending.|
|C2|Parameterise colour, resolution, background image|0.5d|Status: Partially Implemented. The `VideoGenerationRequest` model for the API endpoint supports parameters for resolution and colors. Implementation of these parameters within the Celery video generation task is pending. |
|C3|Expose `/video/{id}` download endpoint|0.5d|Status: Implemented. Completed jobs (including videos) provide an `output_file_url` (e.g., via `/api/library/items/{job_id}` or `/api/jobs/{job_id}`) which points to a generic download mechanism (e.g., `/api/outputs/download/{job_id}/{filename}`). This is available on the `features` branch.|

Deliverable: MP4/WEBM video ready for YouTube.

---

## Milestone 4 – Transcription service (week 4-5)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|D1|Bundle Faster-Whisper in backend image|0.5d|Use GPU if available|
|D2|Create async `transcribe_audio` task|0.5d|Return SRT + plain text|
|D3|Store transcripts in Postgres & filesystem|0.5d|

---

## Milestone 5 – Local LLM integration (week 5-6)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|E1|Add Ollama service to Compose|0.25d|Pull `llama2:7b-chat` by default|
|E2|Endpoint `/ai/suggest` that calls Ollama API|0.5d|Prompt engineering|
|E3|Persist AI suggestions to DB|0.25d|

---

## Milestone 6 – Publishing automation (week 6-7)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|F1|Add n8n container to Compose|0.25d|
|F2|Provide sample YouTube upload workflow|0.5d|Secrets via `.env`|
|F3|Trigger n8n via webhook when processing completes|0.5d|

---

## Milestone 7 – Front-end dashboard (phase 2)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|G1|Spin up React + Vite app (Deferred)|1d|Original plan postponed – simple HTML/JS frontend currently used.|
|G2|Integrate AudioMass as React component (Deferred)|1d|Will resume once React base exists.|
|G3|Implement pages: Library, Editor, Jobs, Settings (Deferred)|2d|APIs ready – UI deferred. The new `/api/library` backend API provides data for the Library page.|
|G4|Socket-based job progress (Planned)|1d|Status: Planned. Detailed strategy outlined in `docs/websocket_integration_plan.md`. See also B4. No implementation work found on the `features` branch for WebSockets.|

---

## Stretch goals

* Multi-user authentication (Keycloak).
* Cloud export profiles (S3, DigitalOcean Spaces etc.).
* Subtitle burn-in to video.

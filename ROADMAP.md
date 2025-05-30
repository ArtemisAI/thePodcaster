# Roadmap – The Podcaster

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
|B1|POST `/audio/upload` endpoint with multipart support|1d|Implemented. Files saved to session-specific dirs. APIs for listing sessions, files within sessions, downloading originals, and deleting sessions now exist. **2025-05-30**: Fixed Nginx proxy configuration that caused `502` on `/api/audio/upload`.|
|B2|Define Celery tasks for `merge_tracks`, `normalize_volume`, etc.|1d|FFmpeg wrapper|
|B3|Persist job status in Postgres (SQLModel)|0.5d|Implemented. `ProcessingJob` model used. APIs for listing/deleting processed files (job outputs) exist.|
|B4|Send progress updates over WebSocket (FastAPI)|1d|Deferred or Future Enhancement.|
|B5|Enhanced File Management APIs|N/A|Implemented. Includes: listing upload sessions, files within sessions; downloading original uploaded files; deleting upload sessions; listing processed/completed job outputs; deleting processed job outputs; managing a separate 'outputs' directory with list, download, delete APIs.|
|B6|Robust Logging and Startup Checks|N/A|Implemented. Logging to `backend/logs/app.log` with rotation. Startup checks for existence and writability of uploads, processed, outputs, and log directories.|
|B7|Configurable per-file upload size limit & graceful 413 errors|N/A|Implemented in `routes_audio.py`, `config.py`, Docker & Nginx. Environment variable: `MAX_UPLOAD_SIZE_MB`.|

Deliverable: user can upload intro, episode, outro; backend returns processed WAV/MP3.

---

## Milestone 3 – Waveform video exporter (week 3-4)

| ID | Task | Est. | Notes |
|----|------|------|-------|
|C1|Implement `generate_waveform_video` Celery task|1d|FFmpeg showwaves filter|
|C2|Parameterise colour, resolution, background image|0.5d|User preferences table|
|C3|Expose `/video/{id}` download endpoint|0.5d|

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
|G1|Spin up React + Vite app|1d|Typescript. Note: Original plan adapted to a simplified HTML/JS frontend. Core backend APIs are available for future advanced frontend development.|
|G2|Integrate AudioMass as React component|1d|Fork & wrap. Note: Original plan adapted to a simplified HTML/JS frontend. Core backend APIs are available for future advanced frontend development.|
|G3|Implement pages: Library, Editor, Jobs, Settings|2d|Note: Original plan adapted to a simplified HTML/JS frontend. Core backend APIs are available for future advanced frontend development.|
|G4|Socket-based job progress|1d|Note: Original plan adapted to a simplified HTML/JS frontend. Core backend APIs are available for future advanced frontend development.|

---

## Stretch goals

* Multi-user authentication (Keycloak).
* Cloud export profiles (S3, DigitalOcean Spaces etc.).
* Subtitle burn-in to video.

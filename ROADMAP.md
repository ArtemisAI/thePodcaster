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
|B1|POST `/audio/upload` endpoint with multipart support|1d|Store to mounted volume|
|B2|Define Celery tasks for `merge_tracks`, `normalize_volume`, etc.|1d|FFmpeg wrapper|
|B3|Persist job status in Postgres (SQLModel)|0.5d|`ProcessingJob` table|
|B4|Send progress updates over WebSocket (FastAPI)|1d|Front-end subscribers|

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
|G1|Spin up React + Vite app|1d|Typescript|
|G2|Integrate AudioMass as React component|1d|Fork & wrap|
|G3|Implement pages: Library, Editor, Jobs, Settings|2d|
|G4|Socket-based job progress|1d|

---

## Stretch goals

* Multi-user authentication (Keycloak).
* Cloud export profiles (S3, DigitalOcean Spaces etc.).
* Subtitle burn-in to video.

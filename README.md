# The Podcaster – Local Podcast Automation Platform

This repository contains a **local-first, fully containerised platform** that helps creators edit, enrich, and publish podcast episodes with minimal effort.

## High-level Goals

1.  Drag-and-drop, browser-based waveform editor (placeholder, manual HTML frontend implemented for core functions).
2.  Automated audio post-processing (FFmpeg) including merging and volume normalization.
3.  One-click waveform video generation for YouTube and socials (FFmpeg).
4.  AI-powered transcription (Faster-Whisper).
5.  Local LLM (Ollama) integration for suggesting titles and summaries.
6.  Automated publishing workflows via n8n webhook triggers.

The stack is designed to **run completely on a single workstation** while taking advantage of any NVIDIA/AMD GPU that may be available (GPU usage for Ollama/Whisper is configurable but not explicitly set up in this version). Everything is shipped through **Docker Compose** for reproducible development and deployments.

---

## Repository Layout

```
📦 thePodcaster
├── backend/               # FastAPI micro-service & async workers (Celery)
│   ├── app/
│   │   ├── api/           # REST endpoints (routes_audio.py, routes_video.py, routes_transcription.py, routes_llm.py, routes_publish.py)
│   │   ├── services/      # Business logic (audio_processing.py, video_processing.py, transcription.py, llm.py, publish.py)
│   │   ├── models/        # Pydantic & DB models (job.py, llm.py, etc.)
│   │   ├── workers/       # Celery worker entry-points (tasks.py)
│   │   ├── db/            # Database setup (database.py)
│   │   ├── utils/         # Utility functions (storage.py, ffmpeg.py)
│   │   ├── config.py      # Application configuration
│   │   └── logging_config.py # Logging setup
│   │   └── main.py        # Uvicorn ASGI bootstrap & main FastAPI app
│   ├── tests/             # Pytest unit tests for API and services
│   └── Dockerfile
├── frontend/              # Simplified static HTML/CSS/JS frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
├── docker-compose.yml     # Local orchestration of all services
└── docs/                  # Architecture diagrams & ADRs (e.g., ROADMAP.md)
```

---

## Key Backend Features Implemented

*   **Audio Processing:** Upload multiple audio tracks (main, intro, outro), merge them, and normalize volume using FFmpeg. Processing is handled asynchronously via Celery.
*   **Waveform Video Generation:** Create videos with waveform visualizations from audio files, customizable with background colors or images, powered by FFmpeg and Celery.
*   **Audio Transcription:** Transcribe audio content using Faster-Whisper, providing both plain text and SRT format. Transcription is an asynchronous Celery task.
*   **LLM Integration:** Connect to a local Ollama instance to generate podcast titles and summaries from transcripts.
*   **Publishing Automation:** Trigger n8n workflows via webhooks, sending job metadata (media paths, titles, summaries, transcripts) for automated distribution.
*   **Job Management:** Track the status of all processing jobs (audio, video, transcription) using a PostgreSQL database.
*   **Structured Logging & Error Handling:** Comprehensive logging across the backend and robust error handling in API and Celery tasks.
*   **API Documentation:** Automatic OpenAPI (Swagger UI) and ReDoc documentation for all API endpoints.
*   **Unit Tests:** Backend components (APIs, services) are covered by unit tests using Pytest.

---

## Simplified Frontend

Due to challenges with the Node.js tooling environment during development, a simplified manual frontend (HTML, CSS, JavaScript) was implemented. It provides core functionality for:
*   Uploading audio files (main, intro, outro) to initiate processing.
*   Basic display of job submission status.
This frontend is served via Nginx and directly interacts with the backend API. It does not require a Node.js build step. The original plan for a React/Vite dashboard (Milestone 7) was adapted to this simpler approach.

---

## Quick Start

```bash
# 1. Ensure Docker and Docker Compose are installed.
# 2. Clone the repository.
# 3. Copy environment template and adjust secrets / paths if necessary (defaults are generally fine for local run)
cp .env.example .env

# 4. Launch the full stack (backend, worker, db, redis, ollama, n8n, frontend-nginx)
docker compose up -d --build

# 5. Pull an LLM model for Ollama (if not already present)
# Example: docker exec -it podcaster-ollama ollama pull llama2:7b-chat
# (The default model used by the backend is defined in .env or backend/app/config.py)

# 6. Open the frontend UI
# This is the simplified HTML frontend.
open http://localhost:3000

# 7. Access the backend API documentation
# OpenAPI (Swagger): http://localhost:8000/api/docs
# ReDoc: http://localhost:8000/api/redoc

# 8. Check backend health and key API groups
# Health: curl http://localhost:8000/api/health
# Audio API: http://localhost:8000/api/audio/ping (example, check /api/docs for full list)
# Video API: http://localhost:8000/api/video/ (check /api/docs)
# Transcription API: http://localhost:8000/api/transcription/ (check /api/docs)
# LLM API: http://localhost:8000/api/llm/ (check /api/docs)
# Publish API: http://localhost:8000/api/publish/ping (check /api/docs)
```

---

## Development Roadmap

The project was divided into 7 major milestones.
*   **Milestones 1-6 (Backend Infrastructure & Features):** Substantially implemented, covering repository structure, CI, audio processing, video generation, transcription, LLM integration, and publishing hooks.
*   **Milestone 7 (Frontend):** Addressed with a simplified manual HTML/CSS/JS UI due to environmental constraints with Node.js tooling during development. The core backend APIs are available for a more advanced frontend to be built in the future.

Refer to `ROADMAP.md` for the original detailed task breakdown.

---

## Licence

All code in this repository is released under the MIT licence unless stated otherwise. Third-party tools retain their respective licences.
```

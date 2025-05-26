# The Podcaster – Local Podcast Automation Platform

This repository contains a **local-first, fully containerised platform** that helps creators edit, enrich, and publish podcast episodes with minimal effort.

High-level goals
1. Drag-and-drop, browser-based waveform editor (AudioMass).
2. Automated audio post-processing (FFmpeg).
3. One-click waveform video generation for YouTube and socials.
4. AI-powered transcription (Whisper / Faster-Whisper).
5. Local LLM (Ollama) that suggests titles and show-note summaries.
6. Automated publishing workflows (n8n) – e.g. upload to YouTube & update RSS.

The stack is designed to **run completely on a single workstation** while taking advantage of any NVIDIA/AMD GPU that may be available.  Everything is shipped through **Docker Compose** for reproducible development and deployments.

---

## Repository layout (to be filled out in subsequent PRs)

```
📦 thePodcaster
├── backend/               # FastAPI micro-service & async workers (Celery)
│   ├── app/
│   │   ├── api/           # REST endpoints
│   │   ├── services/      # Business logic (audio, whisper, llm, publish …)
│   │   ├── models/        # Pydantic & DB models
│   │   ├── workers/       # Celery worker entry-points
│   │   └── main.py        # Uvicorn ASGI bootstrap
│   ├── tests/
│   └── Dockerfile
├── frontend/              # Placeholder for future web UI bundle (React / Vite)
├── docker-compose.yml     # Local orchestration – see below
└── docs/                  # Architecture diagrams & ADRs
```

---

## Quick start (after everything is implemented)

```bash
# 1. Copy environment template and adjust secrets / paths
cp .env.example .env

# 2. Launch the full stack
docker compose up -d --build

# 3. Open the editor UI
open http://localhost:3000    # AudioMass + dashboard

# 4. Hit the API
curl http://localhost:8000/api/health
```

---

## Development roadmap

The project is divided into **7 major milestones** – each is further broken down in the *Roadmap* section delivered alongside this README.

| # | Milestone | Outcome |
|---|-----------|---------|
|1|Repo bootstrap & CI | Repo structured, Docker Compose skeleton, basic FastAPI healthcheck, automated test skeleton, pre-commit hooks|
|2|Audio ingestion & processing | Upload endpoint, FFmpeg pipeline for trimming/concatenation, store outputs on local volume|
|3|Waveform video exporter | Generate 720p/1080p waveform MP4 via FFmpeg filter, expose async task|
|4|Transcription service | Integrate Faster-Whisper, async transcription tasks, transcripts persisted |
|5|Local LLM integration | Run Ollama container, REST call from backend, prompts for title/summary |
|6|Publishing automation | Provide n8n container + example workflow (YouTube upload, RSS update)|
|7|Front-end (Phase 2) | React/Vite dashboard, embed AudioMass, job monitoring, settings pages |

Refer to `ROADMAP.md` for a very detailed task breakdown, estimation, and sequencing.

---

## Licence

All code in this repository is released under the MIT licence unless stated otherwise.  Third-party tools retain their respective licences.

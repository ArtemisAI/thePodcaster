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
    *   APIs for listing and deleting original uploaded files/sessions.
    *   APIs for listing and deleting processed audio files (job outputs).
*   **Flexible File & Output Management:** APIs for managing original uploaded audio files (list, download, delete), processed audio files (list, download, delete), and a separate generic 'outputs' directory with its own file management APIs.
*   **Structured Logging & Error Handling:** Comprehensive logging across the backend and robust error handling in API and Celery tasks. Includes file-based logging to `backend/logs/app.log` and robust startup checks for directory integrity.
*   **API Documentation:** Automatic OpenAPI (Swagger UI) and ReDoc documentation for all API endpoints.
*   **Unit Tests:** Backend components (APIs, services) are covered by unit tests using Pytest.

---

## Simplified Frontend

Due to challenges with the Node.js tooling environment during development, a simplified manual frontend (HTML, CSS, JavaScript) was implemented. It provides core functionality for:
    *   Uploading audio files (main, intro, outro) to initiate processing.
    *   Viewing and downloading processed jobs (Media Library).
    *   Generating additional visualizations (e.g., waveform videos) via a Visualization Dashboard.
This frontend is served via Nginx and directly interacts with the backend API. It does not require a Node.js build step. The original plan for a React/Vite dashboard (Milestone 7) was adapted to this simpler approach.

---

## Setup & Usage

Follow these steps to set up and run The Podcaster locally.

### Prerequisites

- Docker (20.10+)
- Docker Compose (1.29+)
- (Optional) NVIDIA/AMD GPU for accelerated processing

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/thePodcaster.git
   cd thePodcaster
   ```
2. Copy the example environment file and adjust if necessary:
   ```bash
   cp .env.example .env
   ```
3. (Optional) Pull an Ollama model for AI features:
   ```bash
   docker exec -it podcaster-ollama ollama pull llama2:7b-chat
   ```

### Important: Data Directory Permissions

This application uses Docker volumes to store uploaded and processed files in a `./data` directory on your host machine (relative to the `docker-compose.yml` file). On some systems, particularly Linux, Docker might not have default write permissions to this directory if it's created by your user.

**Before launching the services for the first time, ensure the `./data` directory exists and has appropriate permissions.** You can create it and set open permissions (for local development) with:

```bash
mkdir -p ./data
sudo chmod -R 777 ./data
```

For more restrictive permissions, ensure the user running the Docker daemon (or the user ID mapped into the container, typically `root` or the same UID as your host user if user-namespace remapping is not heavily customized) has write access to this directory. The application runs checks on startup and will log a CRITICAL error if the upload directory within `./data/uploads` is not writable, which is a strong indicator of a permissions issue.

### Launching Services

Start all services:
```bash
docker compose up -d
``` 

View service status:
```bash
docker compose ps
``` 

Stop services:
```bash
docker compose down
``` 

### Accessing the Application

- Frontend UI: http://localhost:3005 (or the value of `FRONTEND_PORT` in `.env`)
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- Health check: http://localhost:8000/api/health

### Web Interface Usage

1. Open the Frontend UI in your browser.
2. Upload your audio files (e.g., intro.mp3, main.mp3, outro.mp3).
3. Click **Process** to start audio processing, video generation, and transcription.
4. Monitor job status in the interface.
5. Download results from the UI or find generated assets in `./data`.

### API Examples

For detailed API testing examples using `curl`, please refer to the [API Endpoint Testing Guide](./backend/tests/README.md).

---

## Database Backups

The Podcaster application relies on a PostgreSQL database (managed by the `podcaster-db` service in `docker-compose.yml`) to store crucial information about uploaded files, processing jobs, transcripts, and other metadata. **Regular backups of this database are essential to prevent data loss.**

### Recommendations:

*   **Use `pg_dump`:** The standard PostgreSQL utility `pg_dump` is recommended for creating logical backups of the database. It can be run against the running `podcaster-db` container.
    Example command to create a plain-text SQL dump:
    ```bash
    docker exec -t podcaster-db pg_dump -U podcaster_user -d podcaster_db > backup_$(date +%Y%m%d_%H%M%S).sql
    ```
    (Replace `podcaster_user` and `podcaster_db` if you've changed them in your `.env` file.)
    For more robust backup strategies, consider `pg_dump`'s custom format (`-Fc`) which allows for more flexibility during restoration (e.g., selecting specific tables, parallel restore).

*   **Backup Regularly:** Schedule backups at an interval appropriate for your usage. For active use, daily backups are a good starting point.
*   **Store Backups Securely:** Store your backup files in a safe, separate location, ideally off the machine running the Docker host. Consider cloud storage or a dedicated backup server.
*   **Test Recovery Procedures:** Regularly test restoring your database from backups to ensure the backups are valid and that you are familiar with the recovery process. This can be done by restoring to a separate, temporary PostgreSQL instance.
*   **Backup Docker Volumes (Optional but Recommended):** While `pg_dump` backs up the database content, also consider strategies for backing up the named Docker volume (`postgres_data`) that stores the raw PostgreSQL data files, especially if you have specific point-in-time recovery needs that go beyond logical backups. However, restoring from `pg_dump` is generally more flexible.

Losing the database means losing all records of your podcast processing history and associated metadata. Please establish a robust backup routine.

---

## Development Roadmap

The project was divided into 7 major milestones.
*   Backend infrastructure and core features (Milestones 1-6, with expanded file management capabilities under Milestone 2) are substantially implemented. This covers repository structure, CI, audio processing, video generation, transcription, LLM integration, publishing hooks, and comprehensive file/output management APIs.
*   **Milestone 7 (Frontend):** Addressed with a simplified manual HTML/CSS/JS UI due to environmental constraints with Node.js tooling during development. The core backend APIs are available for a more advanced frontend to be built in the future.

Refer to `ROADMAP.md` for the original detailed task breakdown and the current status of each item.

---

## Licence

All code in this repository is released under the MIT licence unless stated otherwise. Third-party tools retain their respective licences.
```

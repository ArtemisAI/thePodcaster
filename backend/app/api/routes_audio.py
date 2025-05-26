"""Audio-related REST endpoints.

Planned endpoints:

1. `POST /audio/upload` – Receive multipart/form-data with intro, main, outro.
2. `POST /audio/process` – Trigger audio normalization/concatenation.
3. `GET  /audio/{id}`      – Download processed audio file.
"""

# TODO: implement using FastAPI APIRouter and background tasks

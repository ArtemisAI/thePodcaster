import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException # BackgroundTasks removed
from sqlalchemy.orm import Session

from app.models.hook import FileBrowserHookPayload
from app.config import get_settings, Settings
from app.db.database import get_db
# Import the placeholder task
from app.workers.tasks import handle_filebrowser_upload

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/filebrowser/new-upload", status_code=202)
async def handle_filebrowser_new_upload(
    payload: FileBrowserHookPayload,
    # background_tasks: BackgroundTasks, # Removed
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db) # Included if needed for future DB interactions, or job creation here
):
    logger.info(f"Received new upload hook from File Browser: {payload}")

    # The filePath from File Browser is relative to its /srv root.
    # In our setup, /srv in File Browser is mapped to settings.FILEBROWSER_INCOMING_DIR in the backend container.
    # e.g., payload.filePath might be "/my-audio.mp3" or "my-audio.mp3"
    # The absolute path inside the backend container will be /fb_uploads/my-audio.mp3

    # Ensure payload.filePath is treated as relative to the root, remove leading slash if present.
    relative_file_path_str = payload.filePath.lstrip('/')
    absolute_file_path_in_container = settings.FILEBROWSER_INCOMING_DIR / Path(relative_file_path_str)

    logger.info(f"Resolved absolute path in container: {absolute_file_path_in_container}")

    # It's crucial to validate that the path resolves as expected and the file exists.
    # Path.exists() can be blocking. For a truly async operation, this might need
    # to be offloaded (e.g., using aiofiles or running in a threadpool).
    # However, for this initial step, direct check is acceptable for simplicity.
    # Consider security implications: ensure resolved path is within FILEBROWSER_INCOMING_DIR.
    if not absolute_file_path_in_container.is_file(): # Check if it's a file and exists
        logger.error(f"File reported by File Browser does not exist or is not a file at resolved path: {absolute_file_path_in_container}")
        # To prevent path traversal attacks, verify the resolved path is within the expected directory.
        # Path.resolve() can make the path absolute and resolve symlinks.
        resolved_path = absolute_file_path_in_container.resolve()
        if not str(resolved_path).startswith(str(settings.FILEBROWSER_INCOMING_DIR.resolve())):
            logger.error(f"Path traversal attempt detected or misconfigured path. Resolved path {resolved_path} is outside of {settings.FILEBROWSER_INCOMING_DIR.resolve()}")
            raise HTTPException(status_code=400, detail="Invalid file path.")
        raise HTTPException(status_code=404, detail=f"File not found at {payload.filePath}")

    logger.info(f"File {absolute_file_path_in_container} confirmed to exist.")

    # Dispatch the placeholder Celery task using BackgroundTasks for non-blocking behavior.
    # Note: .delay() is for Celery tasks. If handle_filebrowser_upload is not a Celery task yet,
    # calling it directly or via background_tasks.add_task depends on its nature (sync/async).
    # For a synchronous function like our placeholder, add_task is appropriate.
    # If/when it becomes a Celery task, you'd use `handle_filebrowser_upload.delay(...)`.

    # Dispatch the Celery task.
    handle_filebrowser_upload.delay(
        file_path_str=str(absolute_file_path_in_container),
        username=payload.username
    )
    logger.info(f"Celery task `handle_filebrowser_upload` enqueued for file: {absolute_file_path_in_container}")

    return {"message": "Upload event received and task enqueued.", "filePath": payload.filePath, "resolvedPath": str(absolute_file_path_in_container)}

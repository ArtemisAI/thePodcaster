from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import os
import shutil
import logging
from typing import List

from ..utils.storage import OUTPUTS_DIR # Assuming OUTPUTS_DIR is correctly defined in storage.py

router = APIRouter()
logger = logging.getLogger(__name__)

# Helper to prevent directory traversal, can be enhanced
def is_safe_path(basedir: Path, path_to_check: Path) -> bool:
    try:
        return path_to_check.resolve().parent == basedir.resolve()
    except Exception: # Path does not exist or other error
        return False


@router.get("", response_model=List[str])
async def list_output_files():
    logger.info(f"Listing files in OUTPUTS_DIR: {OUTPUTS_DIR}")
    if not OUTPUTS_DIR.exists() or not OUTPUTS_DIR.is_dir():
        logger.error(f"OUTPUTS_DIR {OUTPUTS_DIR} does not exist or is not a directory.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Outputs directory not configured or found.")
    try:
        files = [entry.name for entry in OUTPUTS_DIR.iterdir() if entry.is_file()]
        logger.info(f"Files in OUTPUTS_DIR: {files}")
        return files
    except Exception as e:
        logger.error(f"Error listing files in OUTPUTS_DIR: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error listing output files.")

@router.get("/{filename}")
async def get_output_file(filename: str):
    logger.info(f"Attempting to serve output file '{filename}'.")
    
    # Basic security for filename
    if ".." in filename or filename.startswith("/"):
        logger.warning(f"Potentially malicious filename '{filename}' requested from outputs.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    file_path = OUTPUTS_DIR / filename
    
    # More robust safe path check
    if not file_path.resolve().parent == OUTPUTS_DIR.resolve():
        logger.warning(f"Attempt to access file outside OUTPUTS_DIR: '{filename}' resolved to '{file_path.resolve()}'.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename (path traversal).")

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"Output file '{filename}' not found at path '{file_path}'.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output file not found.")
    
    try:
        # Determine media type (simplified for outputs, can be expanded)
        media_type = "application/octet-stream" # Default, frontend can interpret
        file_ext = Path(filename).suffix.lower()
        if file_ext == ".txt":
            media_type = "text/plain"
        elif file_ext == ".json":
            media_type = "application/json"
        # Add more specific types if known for outputs
        
        logger.info(f"Serving output file '{file_path}' with media type '{media_type}'.")
        return FileResponse(path=file_path, media_type=media_type, filename=filename)
    except Exception as e:
        logger.error(f"Error serving output file '{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error serving output file.")

@router.delete("/{filename}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_output_file(filename: str):
    logger.info(f"Attempting to delete output file: {filename}")

    if ".." in filename or filename.startswith("/"):
        logger.warning(f"Potentially malicious filename '{filename}' for deletion from outputs.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    file_path = OUTPUTS_DIR / filename

    if not file_path.resolve().parent == OUTPUTS_DIR.resolve():
        logger.warning(f"Attempt to delete file outside OUTPUTS_DIR: '{filename}' resolved to '{file_path.resolve()}'.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename (path traversal).")

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"Output file {file_path} not found for deletion.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output file not found.")
    
    try:
        os.remove(file_path)
        logger.info(f"Successfully deleted output file: {file_path}")
    except Exception as e:
        logger.error(f"Error deleting output file {filename} at {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error deleting output file.")

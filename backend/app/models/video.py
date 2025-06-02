from pydantic import BaseModel, Field
from typing import Optional

class VideoGenerationRequest(BaseModel):
    source_audio_path: str = Field(..., description="Path to the source audio file for video generation. This should be an absolute path within the backend container's filesystem (e.g., /data/processed/<job_id>/normalized_audio.mp3 or /data/fb_uploads/user/audio.mp3).")
    # Future parameters like background_image_path, resolution, colors, etc., can be added here.
    # For example:
    # resolution: Optional[str] = Field(default="1280x720", description="Output video resolution, e.g., '1920x1080'.")
    # background_color: Optional[str] = Field(default="black", description="Background color for the video.")
    # waveform_color: Optional[str] = Field(default="white", description="Color of the waveform.")
    # background_image_path: Optional[str] = Field(default=None, description="Optional path to a background image (absolute path in container).")

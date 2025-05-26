"""Audio post-processing helpers using FFmpeg."""

from pathlib import Path
import ffmpeg # Import the actual library
import logging # Standard logging

# Get a logger for this module
logger = logging.getLogger(__name__)

def merge_and_normalize_audio(input_files: list[Path], output_path: Path) -> Path:
    """
    Merges multiple audio files and normalizes the resulting audio using FFmpeg.

    Args:
        input_files: A list of Path objects for the input audio files (e.g., intro, main, outro).
                     The order in the list determines the concatenation order.
        output_path: The Path object for the output (processed) audio file.

    Returns:
        The Path object of the processed audio file.

    Raises:
        ValueError: If the input_files list is empty.
        FileNotFoundError: If any input file does not exist.
        ffmpeg.Error: If any FFmpeg command fails, including details from stderr.
        Exception: For other unexpected errors during processing.
    """
    if not input_files:
        logger.error("Audio processing attempted with no input files.")
        raise ValueError("Input files list cannot be empty.")

    for f_path in input_files:
        if not f_path.exists():
            logger.error(f"Input audio file not found: {f_path}")
            raise FileNotFoundError(f"Input file not found: {f_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Ensured output directory exists: {output_path.parent}")

    ffmpeg_global_args = ['-hide_banner', '-loglevel', 'error'] # Make FFmpeg less verbose, only log errors

    try:
        logger.info(f"Starting audio processing. Input files: {input_files}, Output: {output_path}")
        
        if len(input_files) > 1:
            logger.debug(f"Concatenating {len(input_files)} files.")
            inputs = [ffmpeg.input(str(f)) for f in input_files]
            merged_audio_node = ffmpeg.concat(*inputs, v=0, a=1).node
            logger.debug("Audio files concatenated successfully.")
        else:
            logger.debug("Single audio file provided, no concatenation needed.")
            merged_audio_node = ffmpeg.input(str(input_files[0]))

        # Normalize the audio using loudnorm filter
        # Target LUFS: -16 (common for stereo podcasts), LRA: 11, True Peak: -1.5 dBTP
        logger.debug("Applying loudnorm filter.")
        normalized_audio_node = ffmpeg.filter(merged_audio_node, 'loudnorm', i="-16", lra="11", tp="-1.5")
        
        # Define the output stream with MP3 codec and bitrate
        stream = ffmpeg.output(normalized_audio_node, str(output_path), acodec='mp3', audio_bitrate='192k')
        logger.debug(f"FFmpeg stream configured for output: {str(output_path)}")

        # Execute FFmpeg command
        # Using quiet=False to allow ffmpeg_global_args to control loglevel.
        # If quiet=True, it overrides and silences everything.
        logger.info(f"Executing FFmpeg command for job. Output: {output_path}")
        stdout, stderr = ffmpeg.run(stream, cmd=settings.FFMPEG_PATH if hasattr(settings, 'FFMPEG_PATH') and settings.FFMPEG_PATH else 'ffmpeg', 
                                    global_args=ffmpeg_global_args, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        # Log stdout/stderr from FFmpeg for debugging if needed, though global_args should limit it.
        if stdout: logger.debug(f"FFmpeg stdout: {stdout.decode('utf-8')}")
        if stderr: logger.warning(f"FFmpeg stderr (even with loglevel error, some info might appear): {stderr.decode('utf-8')}") # Use warning for stderr

        logger.info(f"Successfully processed and saved audio to {output_path}")

    except ffmpeg.Error as e:
        # Decode stderr for detailed error message if available
        error_details = e.stderr.decode('utf8') if e.stderr else "No stderr details from FFmpeg."
        logger.error(f"FFmpeg error during audio processing for output {output_path}. Details: {error_details}", exc_info=False) # exc_info=False as we have details
        
        # Attempt to remove partially created output file
        if output_path.exists():
            try:
                output_path.unlink()
                logger.debug(f"Removed partially created file: {output_path}")
            except OSError as os_err:
                logger.error(f"Could not remove partially created file {output_path}: {os_err}", exc_info=True)
        raise  # Re-raise the original ffmpeg.Error to be handled by the caller (e.g., Celery task)
    
    except Exception as e:
        logger.error(f"An unexpected error occurred during audio processing for {output_path}: {e}", exc_info=True)
        if output_path.exists():
             try:
                output_path.unlink()
                logger.debug(f"Removed partially created file due to unexpected error: {output_path}")
             except OSError as os_err:
                logger.error(f"Could not remove partially created file {output_path} after unexpected error: {os_err}", exc_info=True)
        raise # Re-raise the unexpected exception

    return output_path

# Placeholder for FFMPEG_PATH in settings if you want to make it configurable
# from backend.app.config import settings # Assuming settings might have FFMPEG_PATH
# Example: FFMPEG_PATH = getattr(settings, "FFMPEG_PATH", "ffmpeg")
# And then use cmd=FFMPEG_PATH in ffmpeg.run()
# For now, it defaults to 'ffmpeg' in PATH.
# Added settings.FFMPEG_PATH check to ffmpeg.run as an example.
# Ensure `from backend.app.config import settings` is present if using this.

# This requires settings to be importable. If it's not, remove the settings.FFMPEG_PATH part.
# For this example, I'll assume `settings` can be imported.
from backend.app.config import settings

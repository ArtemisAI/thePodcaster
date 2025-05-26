from pathlib import Path
from faster_whisper import WhisperModel
import logging
import time # For SRT timestamp formatting

# Get a logger for this module
logger = logging.getLogger(__name__)

# --- Configuration for Whisper Model ---
# These could be moved to a central config (e.g., backend.app.config.settings) if dynamic configuration is needed.
MODEL_SIZE = "base.en"  # Examples: "base.en", "small.en", "medium.en", "large-v2"
DEVICE_TYPE = "cpu"     # "cpu" or "cuda" (if GPU is available and CUDA-enabled PyTorch is installed)
COMPUTE_TYPE = "int8"   # Examples: "int8", "float16" (for GPU), "float32" (CPU default if not specified)

# --- Whisper Model Initialization ---
# Initialize the model once when the module is loaded.
# This is generally suitable for Celery workers where each worker process loads the model once.
# For a FastAPI app with multiple Uvicorn workers, this might load the model in each worker process.
# Consider lazy loading or a shared model instance if memory is a concern for many Uvicorn workers.
_model_instance = None

def get_whisper_model():
    """Initializes and returns the Whisper model instance. Caches the instance."""
    global _model_instance
    if _model_instance is None:
        try:
            logger.info(f"Initializing Whisper model: Size='{MODEL_SIZE}', Device='{DEVICE_TYPE}', Compute='{COMPUTE_TYPE}'")
            _model_instance = WhisperModel(MODEL_SIZE, device=DEVICE_TYPE, compute_type=COMPUTE_TYPE)
            logger.info("Whisper model initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model (Size: {MODEL_SIZE}, Device: {DEVICE_TYPE}): {e}", exc_info=True)
            # Depending on desired behavior, could raise an error here or let it be None,
            # causing transcribe_audio to fail if the model isn't available.
            # For now, let it be None, and transcribe_audio will handle it.
            _model_instance = None # Explicitly set to None on failure
    return _model_instance

# --- SRT Timestamp Formatting ---
def format_timestamp_srt(seconds: float) -> str:
    """Converts seconds to SRT time format (HH:MM:SS,ms)"""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    secs = milliseconds // 1_000 # Renamed from 'seconds' to avoid conflict
    milliseconds -= secs * 1_000

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

# --- Transcription Function ---
def transcribe_audio(audio_input_path: Path) -> tuple[str, str]:
    """
    Transcribes an audio file using the pre-loaded Whisper model.

    Args:
        audio_input_path: Path to the input audio file.

    Returns:
        A tuple containing:
            - plain_text_transcript (str): The full transcript as plain text.
            - srt_transcript (str): The transcript in SRT format.
    
    Raises:
        FileNotFoundError: If the audio input file does not exist.
        RuntimeError: If the Whisper model failed to initialize or transcription fails.
        Exception: For other unexpected errors during transcription.
    """
    model = get_whisper_model()
    if not model:
        logger.error("Whisper model is not available. Cannot transcribe.")
        # This error will be caught by the Celery task and job status updated.
        raise RuntimeError("Whisper model is not initialized or failed to load.")

    if not audio_input_path.exists():
        logger.error(f"Audio input file for transcription not found: {audio_input_path}")
        raise FileNotFoundError(f"Audio input file not found: {audio_input_path}")

    logger.info(f"Starting transcription for: {audio_input_path}")
    
    plain_text_parts = []
    srt_parts = []
    segment_idx = 1

    try:
        # beam_size can be adjusted. word_timestamps=True can provide word-level detail if needed.
        # For longer audio, consider parameters like `vad_filter=True` if VAD support is robust.
        segments, info = model.transcribe(str(audio_input_path), beam_size=5) 
        
        logger.info(f"Transcription details - Detected language: '{info.language}' (Prob: {info.language_probability:.2f}), Duration: {info.duration:.2f}s")

        for segment in segments:
            plain_text_parts.append(segment.text.strip())
            
            start_time_srt = format_timestamp_srt(segment.start)
            end_time_srt = format_timestamp_srt(segment.end)
            srt_parts.append(str(segment_idx))
            srt_parts.append(f"{start_time_srt} --> {end_time_srt}")
            srt_parts.append(segment.text.strip())
            srt_parts.append("") # Blank line separator for SRT entries
            segment_idx += 1
            
            logger.debug(f"Segment {segment_idx-1}: [{start_time_srt} --> {end_time_srt}] \"{segment.text.strip()}\"")

    except Exception as e:
        # Catching a broad Exception as errors from faster-whisper might not always be specific custom errors.
        logger.error(f"Error during Whisper model transcription for {audio_input_path}: {e}", exc_info=True)
        # Re-raise as a RuntimeError to indicate a problem during the transcription process itself.
        raise RuntimeError(f"Transcription failed for {audio_input_path}: {str(e)}")

    plain_text_transcript = " ".join(plain_text_parts)
    srt_transcript = "\n".join(srt_parts)
    
    logger.info(f"Successfully transcribed {audio_input_path}. Total segments: {segment_idx-1}")
    return plain_text_transcript, srt_transcript

# Example of how to test this service (can be commented out or removed for production)
if __name__ == "__main__":
    # This section only runs if `python -m backend.app.services.transcription` is executed.
    # Configure basic logging for the test.
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    
    # Create a dummy MP3 file for testing if it doesn't exist.
    # Note: This requires ffmpeg to be installed if you want to generate a real silent audio.
    # For simplicity, we'll just create an empty file and expect transcription to likely fail or produce empty results.
    # A proper test would use a small, actual audio sample.
    test_audio_file = Path("dummy_test_audio.mp3")
    if not test_audio_file.exists():
        try:
            # Attempt to create a short silent MP3 using ffmpeg if available
            # This is more robust for testing the transcription pipeline than an empty file.
            import subprocess
            subprocess.run(
                ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-t", "1", "-q:a", "9", str(test_audio_file)],
                check=True, capture_output=True
            )
            logger.info(f"Created dummy audio file: {test_audio_file}")
        except Exception as e:
            logger.warning(f"Could not create dummy audio file with ffmpeg ({e}). Creating empty file as fallback for {test_audio_file}.")
            test_audio_file.write_text("This is not a real audio file.") # Fallback

    if test_audio_file.exists():
        logger.info(f"Attempting to transcribe test file: {test_audio_file.resolve()}")
        try:
            text, srt = transcribe_audio(test_audio_file)
            print("\n--- Plain Text Transcript ---")
            print(text if text else "[No text transcribed]")
            print("\n--- SRT Transcript ---")
            print(srt if srt else "[No SRT content transcribed]")
        except Exception as e:
            print(f"Error during example transcription: {e}")
    else:
        print(f"Test audio file {test_audio_file} could not be created/found. Skipping example.")

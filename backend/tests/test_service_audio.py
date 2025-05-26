import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY
import ffmpeg # Import the actual library to check for ffmpeg.Error

# Import the function to test
from backend.app.services.audio_processing import merge_and_normalize_audio

@pytest.fixture
def mock_ffmpeg_methods():
    with patch("ffmpeg.input") as mock_input, \
         patch("ffmpeg.concat") as mock_concat, \
         patch("ffmpeg.filter") as mock_filter, \
         patch("ffmpeg.output") as mock_output, \
         patch("ffmpeg.run") as mock_run:
        
        # Configure mocks to return new mock objects to allow chaining
        mock_input_instance = MagicMock()
        mock_input.return_value = mock_input_instance
        
        # For concat, it needs to return a node that can be passed to filter or output
        mock_concat_node = MagicMock()
        mock_concat.return_value = mock_concat_node
        
        # filter also needs to return a node
        mock_filter_node = MagicMock()
        mock_filter.return_value = mock_filter_node

        # input_instance itself (if used directly in filter/output) should also be chainable
        mock_input_instance.filter.return_value = mock_filter_node # e.g. input_audio.filter(...)
        # If concat is used, its result is passed to filter:
        mock_concat_node.filter.return_value = mock_filter_node # e.g. merged_audio.filter(...)
                                                                # This is tricky if the code uses ffmpeg.filter(node, ...)

        yield {
            "input": mock_input,
            "concat": mock_concat,
            "filter": mock_filter, # This is the module-level filter
            "output": mock_output,
            "run": mock_run,
            "mock_input_instance": mock_input_instance, # To check calls on the object returned by ffmpeg.input()
            "mock_concat_node": mock_concat_node,
            "mock_filter_node": mock_filter_node,
        }

@pytest.fixture
def temp_audio_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "test_audio.mp3"
    file_path.write_text("dummy audio content") # Create a dummy file
    return file_path

@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "processed"
    output_dir.mkdir()
    return output_dir

def test_merge_and_normalize_single_file(mock_ffmpeg_methods, temp_audio_file: Path, temp_output_dir: Path):
    output_path = temp_output_dir / "normalized.mp3"
    
    result_path = merge_and_normalize_audio([temp_audio_file], output_path)
    
    assert result_path == output_path
    mock_ffmpeg_methods["input"].assert_called_once_with(str(temp_audio_file))
    
    # Check that loudnorm filter was applied
    # The actual call might be ffmpeg.filter(mock_input_instance, 'loudnorm', ...) 
    # or mock_input_instance.filter('loudnorm', ...) depending on how it's written.
    # Given the service code structure: ffmpeg.filter(input_audio, 'loudnorm', ...)
    # So, mock_ffmpeg_methods["filter"] should be called.
    # The first argument to ffmpeg.filter would be the node from ffmpeg.input()
    mock_ffmpeg_methods["filter"].assert_any_call(mock_ffmpeg_methods["mock_input_instance"], 'loudnorm', i=ANY, lra=ANY, tp=ANY)
    
    mock_ffmpeg_methods["output"].assert_called_once_with(ANY, str(output_path), acodec='mp3', audio_bitrate='192k')
    mock_ffmpeg_methods["run"].assert_called_once()
    mock_ffmpeg_methods["concat"].assert_not_called() # Should not be called for single file


def test_merge_and_normalize_multiple_files(mock_ffmpeg_methods, temp_audio_file: Path, temp_output_dir: Path):
    # Create more dummy files for testing merge
    intro_file = temp_audio_file.parent / "intro.mp3"
    intro_file.write_text("intro content")
    outro_file = temp_audio_file.parent / "outro.mp3"
    outro_file.write_text("outro content")
    
    input_files = [intro_file, temp_audio_file, outro_file]
    output_path = temp_output_dir / "merged_normalized.mp3"
    
    result_path = merge_and_normalize_audio(input_files, output_path)
    
    assert result_path == output_path
    
    # Check ffmpeg.input calls
    assert mock_ffmpeg_methods["input"].call_count == len(input_files)
    mock_ffmpeg_methods["input"].assert_any_call(str(intro_file))
    mock_ffmpeg_methods["input"].assert_any_call(str(temp_audio_file))
    mock_ffmpeg_methods["input"].assert_any_call(str(outro_file))
    
    # Check ffmpeg.concat call
    # It's called with multiple ffmpeg.input stream objects
    mock_ffmpeg_methods["concat"].assert_called_once_with(ANY, ANY, ANY, v=0, a=1) 
                                                        #ANY because these are mock objects from input()

    # Check that loudnorm filter was applied to the result of concat
    # The first argument to ffmpeg.filter should be the node from ffmpeg.concat()
    mock_ffmpeg_methods["filter"].assert_any_call(mock_ffmpeg_methods["mock_concat_node"], 'loudnorm', i=ANY, lra=ANY, tp=ANY)
    
    mock_ffmpeg_methods["output"].assert_called_once_with(ANY, str(output_path), acodec='mp3', audio_bitrate='192k')
    mock_ffmpeg_methods["run"].assert_called_once()


def test_merge_and_normalize_ffmpeg_error(mock_ffmpeg_methods, temp_audio_file: Path, temp_output_dir: Path):
    output_path = temp_output_dir / "error_output.mp3"
    
    # Simulate ffmpeg.run raising an error
    # The error object should have a stderr attribute if the service tries to decode it
    mock_ffmpeg_methods["run"].side_effect = ffmpeg.Error("ffmpeg_run_failed", stdout=None, stderr=b"Error details from ffmpeg")
    
    with pytest.raises(ffmpeg.Error) as excinfo:
        merge_and_normalize_audio([temp_audio_file], output_path)
    
    assert "ffmpeg_run_failed" in str(excinfo.value)
    # Check if the partially created file is attempted to be unlinked
    # This requires output_path.exists() to be True then output_path.unlink() to be called
    # This can be complex to mock perfectly without more intricate fs mocking.
    # For now, ensuring the error propagates is the main goal.


def test_merge_and_normalize_input_file_not_found(temp_output_dir: Path):
    non_existent_file = Path("/path/to/non_existent_audio.mp3")
    output_path = temp_output_dir / "output.mp3"
    
    with pytest.raises(FileNotFoundError):
        merge_and_normalize_audio([non_existent_file], output_path)

def test_merge_and_normalize_no_input_files(temp_output_dir: Path):
    output_path = temp_output_dir / "output.mp3"
    with pytest.raises(ValueError, match="Input files list cannot be empty."):
        merge_and_normalize_audio([], output_path)

# Note on mocking ffmpeg-python:
# The library uses a fluent interface (chaining). Mocks need to return mocks
# that can be further called.
# - `ffmpeg.input()` returns an `InputStream` instance.
# - `ffmpeg.concat()` takes `InputStream` objects and returns a `Stream` (a node).
# - `ffmpeg.filter()` (module level) takes a `Stream` (node) and filter args, returns a new `Stream`.
# - `InputStream` and `Stream` objects also have a `.filter()` method.
# - `ffmpeg.output()` takes a `Stream` (or multiple) and filename, returns a `OutputStreamSpec`.
# - `ffmpeg.run()` takes an `OutputStreamSpec`.
# The `mock_ffmpeg_methods` fixture tries to accommodate some of this.
# The key is that the objects returned by `mock_input` and `mock_concat`
# must themselves be mocks that can have `.filter()` called on them, or be passed to `ffmpeg.filter()`.
# The current `merge_and_normalize_audio` uses `ffmpeg.filter(node, ...)`.
# `ANY` from `unittest.mock` is used for arguments we don't need to assert specific values for,
# especially for mock stream objects.
# `ffmpeg.Error` is imported to be raised by the mock and caught by the test.
# `tmp_path` pytest fixture is used for creating temporary files and directories.
# The service creates the output directory if it doesn't exist, so tests should reflect that.
# (output_path.parent.mkdir(parents=True, exist_ok=True) is called in service)
# The tests assume `ffmpeg-python` is installed in the environment where tests run.
# FileNotFoundError is tested by providing a path that won't exist.
# The `mock_filter` in `mock_ffmpeg_methods` refers to the `ffmpeg.filter` function.
# The `mock_input_instance.filter` or `mock_concat_node.filter` would be for `node.filter(...)` style calls.
# In `merge_and_normalize_audio`, it seems `ffmpeg.filter(merged_audio, ...)` is used,
# so the `mock_filter` should catch it, with `merged_audio` (the node from concat or input) as the first arg.
# `assert_any_call` is used for `ffmpeg.filter` because it might be called as part of a complex chain,
# and we are primarily interested if 'loudnorm' was applied to the correct type of node.
# The `ANY` for `i, lra, tp` in loudnorm means we are not testing the specific normalization values here.
# The `mock_ffmpeg_methods["mock_input_instance"]` and `mock_ffmpeg_methods["mock_concat_node"]` are passed
# to `assert_any_call` to verify that `ffmpeg.filter` was called with the output of `ffmpeg.input` or `ffmpeg.concat`.
# This is a bit indirect; a more direct way would be if `ffmpeg.filter` returned a new mock that `ffmpeg.output` then receives.
# However, the current setup checks the flow reasonably well.

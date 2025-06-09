import pytest
import httpx # Import for httpx.RequestError, httpx.HTTPStatusError
from unittest.mock import patch, AsyncMock
import json

# Import the function to test and the settings
from app.services.llm import generate_suggestions, PROMPT_TEMPLATES
from app.config import settings

# --- Test Cases ---

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_title_summary_success(mock_post):
    sample_transcript = "This is a test transcript."
    prompt_type = "title_summary"
    expected_model_output = {"titles": ["Title 1"], "summary": "Summary 1"}
    
    # Mock the response from Ollama
    # Ollama's response structure: {"model": ..., "created_at": ..., "response": "{\"titles\": [...], \"summary\": \"...\"}", ...}
    # The "response" field contains a JSON *string*.
    mock_ollama_response_content = {
        "model": settings.OLLAMA_DEFAULT_MODEL,
        "created_at": "2023-10-26T12:00:00Z",
        "response": json.dumps(expected_model_output), # This is crucial: response is a JSON string
        "done": True
    }
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_ollama_response_content
    mock_response.raise_for_status = MagicMock() # Does nothing if called, no HTTP error
    mock_post.return_value = mock_response
    
    result = await generate_suggestions(sample_transcript, prompt_type=prompt_type)
    
    assert result == expected_model_output
    
    # Verify httpx.AsyncClient.post was called correctly
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    
    # args[0] should be the URL
    assert args[0] == f"{settings.OLLAMA_URL}/api/generate"
    
    # kwargs['json'] should be the payload
    payload = kwargs['json']
    assert payload["model"] == settings.OLLAMA_DEFAULT_MODEL
    assert payload["prompt"] == PROMPT_TEMPLATES[prompt_type].format(transcript=sample_transcript)
    assert payload["stream"] is False
    assert payload["format"] == "json"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_title_only_success(mock_post):
    sample_transcript = "Another transcript for titles."
    prompt_type = "title_only"
    expected_model_output = {"titles": ["Title A", "Title B"]}
    
    mock_ollama_response_content = {
        "response": json.dumps(expected_model_output)
        # other fields omitted for brevity
    }
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_ollama_response_content
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    result = await generate_suggestions(sample_transcript, prompt_type=prompt_type)
    assert result == expected_model_output
    # Verify prompt construction for title_only
    payload = mock_post.call_args.kwargs['json']
    assert payload["prompt"] == PROMPT_TEMPLATES[prompt_type].format(transcript=sample_transcript)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_summary_only_success(mock_post):
    sample_transcript = "A transcript for summary."
    prompt_type = "summary_only"
    expected_model_output = {"summary": "This is just a summary."}
    
    mock_ollama_response_content = {"response": json.dumps(expected_model_output)}
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_ollama_response_content
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    result = await generate_suggestions(sample_transcript, prompt_type=prompt_type)
    assert result == expected_model_output
    payload = mock_post.call_args.kwargs['json']
    assert payload["prompt"] == PROMPT_TEMPLATES[prompt_type].format(transcript=sample_transcript)


@pytest.mark.asyncio
async def test_generate_suggestions_invalid_prompt_type():
    with pytest.raises(ValueError, match="Invalid prompt_type: unknown_type"):
        await generate_suggestions("test", prompt_type="unknown_type")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_ollama_http_error(mock_post):
    mock_post.side_effect = httpx.HTTPStatusError(
        "Ollama server error", 
        request=MagicMock(), 
        response=MagicMock(status_code=500, text="Internal Server Error")
    )
    with pytest.raises(httpx.HTTPStatusError):
        await generate_suggestions("test", prompt_type="title_summary")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_ollama_request_error(mock_post):
    mock_post.side_effect = httpx.RequestError("Connection failed", request=MagicMock())
    with pytest.raises(httpx.RequestError):
        await generate_suggestions("test", prompt_type="title_summary")


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_ollama_response_json_decode_error(mock_post):
    # Ollama responds 200, but the "response" field is not valid JSON
    mock_ollama_response_content = {"response": "This is not JSON"}
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_ollama_response_content
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    result = await generate_suggestions("test", prompt_type="title_summary")
    assert "error" in result
    assert "Failed to parse LLM response JSON" in result["error"]
    assert result["details"] == "This is not JSON"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_ollama_response_missing_response_field(mock_post):
    # Ollama responds 200, but the expected "response" field is missing entirely
    mock_ollama_response_content = {"model": "test_model", "done": True} # No "response" field
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_ollama_response_content
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    result = await generate_suggestions("test", prompt_type="title_summary")
    assert "error" in result
    assert "Ollama response missing 'response' field" in result["error"]


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_llm_output_malformed_titles(mock_post):
    # Test case where 'titles' is expected but not a list
    sample_transcript = "Transcript for malformed titles."
    prompt_type = "title_summary"
    malformed_llm_output = {"titles": "This should be a list", "summary": "Correct summary."}
    
    mock_ollama_response_content = {"response": json.dumps(malformed_llm_output)}
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_ollama_response_content
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    result = await generate_suggestions(sample_transcript, prompt_type=prompt_type)
    # The service currently tries to be lenient and returns what it can
    assert result["titles"] == [] # Should default to empty list or handle error
    assert result["summary"] == "Correct summary."


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_generate_suggestions_llm_output_malformed_summary(mock_post):
    # Test case where 'summary' is expected but not a string
    sample_transcript = "Transcript for malformed summary."
    prompt_type = "title_summary"
    malformed_llm_output = {"titles": ["Correct Title"], "summary": ["This should be a string"]}
    
    mock_ollama_response_content = {"response": json.dumps(malformed_llm_output)}
    mock_response = AsyncMock()
    mock_response.json.return_value = mock_ollama_response_content
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response
    
    result = await generate_suggestions(sample_transcript, prompt_type=prompt_type)
    assert result["titles"] == ["Correct Title"]
    assert result["summary"] == "Could not extract summary." # Default or error message

# Key aspects for testing generate_suggestions:
# 1. Mocking `httpx.AsyncClient.post`: This is the primary external interaction.
#    - Use `AsyncMock` for async methods.
#    - Ensure the mock's `return_value` (which is a mock response object) also has methods like `json()` and `raise_for_status()` mocked.
#    - `json()` should return the expected Python dict that Ollama's /api/generate endpoint would give.
#    - Crucially, Ollama's `response` field within that dict is a JSON *string*, so `json.dumps()` is used to simulate this.
# 2. Verifying the call to Ollama:
#    - Check the URL.
#    - Check the payload, especially the `model`, `prompt`, `stream`, and `format` fields.
#    - The prompt construction logic (using `PROMPT_TEMPLATES`) is important to verify.
# 3. Handling different Ollama responses:
#    - Successful response with valid JSON in the "response" field.
#    - Successful response but the "response" field is not valid JSON (JSONDecodeError).
#    - Successful response but the "response" field is missing.
#    - Successful response but the JSON in "response" doesn't match expected structure (e.g., missing "titles" or "summary").
# 4. Handling HTTP errors from Ollama (e.g., 500 status code, connection errors).
#    - `mock_post.side_effect` is used for this.
# 5. Testing different `prompt_type` values to ensure the correct template is used.
# 6. Testing edge cases like invalid `prompt_type`.
# `settings.OLLAMA_URL` and `settings.OLLAMA_DEFAULT_MODEL` are used from the actual config,
# which is fine as they define the target for the mocked call.
# The service's error handling (e.g., returning partial data or specific error dicts) should be reflected in assertions.
# The current service logic for malformed but parsable JSON in the 'response' field tries to return partial data.
# e.g. if 'titles' is not a list, it returns `{"titles": [], "summary": "..."}`. This behavior is tested.
# If 'summary' is not a string, it returns `{"summary": "Could not extract summary."}`. This is tested.
# If the JSON string itself inside 'response' is unparsable, it returns `{"error": "Failed to parse LLM response JSON", ...}`. This is tested.
# If the 'response' field is missing from Ollama's main JSON, it returns `{"error": "Ollama response missing 'response' field", ...}`. This is tested.

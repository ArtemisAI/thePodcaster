import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from importlib import reload

from app.models.job import ProcessingJob, JobStatus
from app.models.llm import LLMSuggestion
from backend.app import config as config_module

# reload config to apply env vars in each test

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_trigger_n8n_workflow_success(mock_post, monkeypatch):
    monkeypatch.setenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/test")
    monkeypatch.setenv("N8N_API_KEY", "secret")
    reload(config_module)
    import sys
    sys.modules['backend.app.models.job'] = sys.modules['app.models.job']
    sys.modules['backend.app.models.llm'] = sys.modules['app.models.llm']
    sys.modules['backend.app.models.audio'] = sys.modules['app.models.audio']
    sys.modules['backend.app.models.transcript'] = sys.modules['app.models.transcript']
    from app.services import publish
    monkeypatch.setattr(publish, "settings", config_module.settings)

    job = ProcessingJob(id=1, job_type="video_generation", status=JobStatus.COMPLETED,
                        output_file_path="outputs/out.mp4")
    job.input_file_path = "uploads/in.mp3"
    job.created_at = datetime.utcnow()

    suggestion = MagicMock()
    suggestion.get_titles.return_value = ["T1"]
    suggestion.suggested_summary = "S"
    suggestion.job = job

    def query_side_effect(model):
        q = MagicMock()
        if model is LLMSuggestion:
            q.filter.return_value.order_by.return_value.first.return_value = suggestion
        elif model is ProcessingJob:
            q.filter.return_value.first.return_value = job
        return q

    db = MagicMock()
    db.query.side_effect = query_side_effect

    mock_response = AsyncMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    result = await publish.trigger_n8n_workflow(job, db)
    assert result["success"] is True
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["job_id"] == 1
    assert payload["media_type"] == "video"


@pytest.mark.asyncio
async def test_trigger_n8n_workflow_no_url(monkeypatch):
    monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("N8N_API_KEY", raising=False)
    reload(config_module)
    import sys
    sys.modules['backend.app.models.job'] = sys.modules['app.models.job']
    sys.modules['backend.app.models.llm'] = sys.modules['app.models.llm']
    sys.modules['backend.app.models.audio'] = sys.modules['app.models.audio']
    sys.modules['backend.app.models.transcript'] = sys.modules['app.models.transcript']
    from app.services import publish
    monkeypatch.setattr(publish, "settings", config_module.settings)

    job = ProcessingJob(id=2, job_type="video_generation", status=JobStatus.COMPLETED)
    db = MagicMock()

    with pytest.raises(ValueError):
        await publish.trigger_n8n_workflow(job, db)

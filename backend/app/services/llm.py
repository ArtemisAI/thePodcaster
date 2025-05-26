"""Abstraction layer around the Ollama REST API."""

# Planned public API:
#
# async def generate_title_summary(transcript: str, model: str = "llama2") -> dict:
#     """Return {"title": str, "summary": str}"""
#
# Implementation steps:
# 1. Build prompt template.
# 2. POST to f"{settings.OLLAMA_URL}/api/generate".
# 3. Stream or aggregate response.

# TODO: implement using httpx.AsyncClient

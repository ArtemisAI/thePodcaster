"""Endpoints to trigger publishing workflows (via n8n)."""

# Planned endpoints:
# * POST /publish/youtube – Trigger YouTube upload workflow in n8n.
# * POST /publish/rss     – Update RSS feed with episode metadata.

from fastapi import APIRouter

router = APIRouter()

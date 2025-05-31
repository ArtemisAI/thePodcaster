"""Endpoints for Whisper/Faster-Whisper transcription tasks."""

# Planned endpoints:
# * POST /transcription        – start transcription for given audio id.
# * GET  /transcription/{id}   – get transcript & status.

from fastapi import APIRouter

router = APIRouter()

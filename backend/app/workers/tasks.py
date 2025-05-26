"""Celery task definitions.

Declare background jobs for CPU/GPU intensive work:

* `process_audio_task`
* `generate_waveform_task`
* `transcribe_task`
* `ai_suggest_task`

Celery config should reside in the same module for auto-discovery.
"""

# TODO: set up Celery app and task functions calling services.* modules

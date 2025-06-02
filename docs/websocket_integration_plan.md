# WebSocket Integration Plan for Real-time Progress Updates

This document outlines the plan for integrating WebSocket functionality into The Podcaster platform to provide real-time progress updates for long-running background tasks (e.g., audio processing, video generation, transcription). This corresponds to Roadmap items B4 and G4.

## 1. Overview

The goal is to allow the frontend to connect to a WebSocket endpoint and receive messages from the backend whenever a Celery task (worker) makes progress or changes status.

## 2. Backend Changes

### 2.1. FastAPI WebSocket Endpoint

*   **Create a new WebSocket endpoint:**
    *   Location: Potentially `ws://localhost:8000/api/ws/progress/{job_id}` or `ws://localhost:8000/api/ws/progress?job_id={job_id}`.
    *   This endpoint will handle WebSocket connections from clients interested in a specific job's progress.
    *   It should manage active connections, possibly storing them in a dictionary keyed by `job_id`.
*   **Authentication:** Consider if/how WebSocket connections should be authenticated, especially if dealing with user-specific jobs in the future. For now, `job_id` based subscription might be sufficient.

### 2.2. Celery Worker Progress Publishing

*   **Mechanism:** Celery workers need a way to send progress updates back to the FastAPI application. Redis Pub/Sub is a suitable candidate for this:
    *   Workers will publish messages to a specific Redis channel, perhaps dynamically named (e.g., `progress_updates:{job_id}`).
    *   The message should contain `job_id`, `progress_percentage`, `status_message`, and current `job_status`.
*   **Task Integration:**
    *   Modify Celery tasks in `backend/app/workers/tasks.py` (and any other relevant task files) to publish these updates at key stages of processing.
    *   Example: `self.update_state(state='PROGRESS', meta={'progress': 50, 'message': 'Normalizing audio...'})` in Celery can be a source, but direct Redis publishing might be more flexible for real-time messages outside of Celery's own state updates.

### 2.3. FastAPI Message Forwarding (Redis to WebSocket)

*   **Redis Subscriber:** The FastAPI application (or a dedicated part of it) will need to subscribe to the Redis Pub/Sub channels.
    *   When a message is received from Redis for a `job_id`, the FastAPI app will look up all active WebSocket clients subscribed to that `job_id`.
    *   It will then send the progress message to each of these connected clients.
*   **Async Handling:** This needs to be handled asynchronously to avoid blocking. FastAPI's `lifespan` events can be used to start and stop the Redis subscriber.

## 3. Frontend Changes

*   **WebSocket Client:**
    *   The JavaScript frontend (`frontend/script.js`) will need to establish a WebSocket connection to the backend endpoint when a user is viewing a job that is processing, or when a new job is initiated.
    *   It should listen for incoming messages.
*   **UI Updates:**
    *   On receiving a progress message, the UI should update dynamically (e.g., update a progress bar, display status messages).
    *   Handle WebSocket connection errors and disconnections gracefully.

## 4. Message Format

A consistent JSON message format should be used for communication over WebSockets and potentially Redis Pub/Sub.

**Example Message from Worker (to Redis) / Backend (to WebSocket):**

```json
{
  "job_id": "some_job_identifier_or_id",
  "type": "progress_update", // or "status_change", "error", "complete"
  "data": {
    "progress_percentage": 75,
    "current_step_message": "Generating waveform video...",
    "job_status": "PROCESSING" // Reflects ProcessingJob.status
  },
  "timestamp": "2023-10-27T10:30:00Z"
}
```

**Considerations for Message Types:**
*   `progress_update`: For incremental progress.
*   `status_change`: When the overall job status changes (e.g., PENDING -> PROCESSING, PROCESSING -> COMPLETED).
*   `job_completed`: A final message indicating success, perhaps with a link to the output.
*   `job_failed`: A message indicating failure, with an error message.

## 5. Implementation Steps (High-Level)

1.  **Setup Redis Pub/Sub:** Ensure Redis is correctly configured and accessible.
2.  **Implement Publisher in Celery Tasks:** Modify tasks to send JSON messages to Redis channels.
3.  **Develop FastAPI WebSocket Endpoint:** Create the `/ws/progress/{job_id}` endpoint.
4.  **Implement Redis Subscriber & Forwarder in FastAPI:** Listen to Redis and relay messages to WebSockets.
5.  **Develop Frontend WebSocket Client:** Connect to the endpoint and handle incoming messages.
6.  **Update UI:** Display real-time progress information.
7.  **Testing:** Thoroughly test the end-to-end flow.

## 6. Open Questions/Considerations

*   **Scalability:** For a large number of concurrent jobs and clients, ensure the Redis Pub/Sub and WebSocket connection management are efficient.
*   **Error Handling:** Robust error handling for WebSocket disconnections, Redis issues, etc.
*   **Security:** Reiterate authentication/authorization for WebSocket connections if sensitive data is involved.
*   **Granularity of Updates:** Decide how frequently workers should send updates to avoid overwhelming the system or the UI.
*   **Alternative to Redis Pub/Sub:** While Redis Pub/Sub is a good fit, other message brokers could be considered if already in the stack or if specific features are needed (e.g., RabbitMQ, Kafka, though likely overkill for this specific use case).

This plan provides a starting point. Details will be refined during implementation.

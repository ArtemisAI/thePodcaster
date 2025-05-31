# Upload & Processing Flow – The Podcaster

This document gives a **step-by-step overview** of how an audio file travels
through the platform – from the moment the user clicks *Upload & Process* in
the browser until the background worker starts crunching the data.  It is
aimed at contributors who need to debug or extend the pipeline.

---

## 1. Front-end (HTML + Vanilla JS)

1. The user selects one mandatory *Main Track* and (optionally) *Intro* / *Outro* files.
2. `script.js`
   * validates the file **type** (see `ALLOWED_AUDIO_TYPES`) and – indirectly –
     the **size** (the back-end enforces the real limit),
   * disables the *Upload & Process* button until the form is valid,
   * on *submit* calls `handleUploadAndProcess()`.
3. `handleUploadAndProcess()`
   1. Creates a `FormData` object and appends the file objects under the field
      names expected by the API (`main_track`, `intro`, `outro`).
   2. Sends a `POST /api/audio/upload` request **without** any auth headers –
      the platform is single-user in early development.
   3. Parses the JSON response `{ "upload_session_id": "…" }`.
   4. Immediately issues `POST /api/audio/process/{upload_session_id}` to start
      the heavy lifting.

If either request fails, the promise is rejected, the spinner disappears and a
screen-reader-friendly error message is rendered into `#uploadResponse`.

## 2. Back-end (FastAPI)

1. `routes_audio.upload_audio()` receives the multipart request.
2. For each upload field it calls `save_uploaded_file()` which
   * streams the file to **`/data/uploads/{session_id}/`** while enforcing the
     `MAX_UPLOAD_SIZE_MB` limit,
   * records a row in `audio_files` (see `models/audio.py`).
3. A `201`-style JSON response with the generated **`upload_session_id`** is
   returned.

## 3. Triggering background processing

`routes_audio.process_audio()` (invoked by the second request) creates a
`ProcessingJob` DB row and enqueues a Celery task (`process_audio_task.delay`)
that will eventually:

* Normalise loudness,
* Concatenate *Intro → Main → Outro*,
* Save the resulting file under **`/data/processed/`**,
* Update the `jobs` table to `status = COMPLETED` (or `FAILED`).

The front-end currently polls the *Jobs* view manually (user clicks *Refresh*);
WebSockets will be added in Milestone G4.

---

### Sequence diagram (textual)

```text
User        Browser           FastAPI                Celery Worker
 |            |                   |                           |
 |------File selection----------->|                           |
 |            |                   |                           |
 |---POST /audio/upload---------->|                           |
 |            |<-- 200 + session--|                           |
 |            |                   |                           |
 |---POST /audio/process/{id}---->|-- DB insert Job ---------->|
 |            |<-- 202 + job_id --|                           |
 |            |                   |                           |
 |            |                   |<-- run process_audio -----|
 |            |                   |--- job status → DB ------>|
```

---

## 4. Error handling & logging

* All server side steps are logged to **`backend/logs/app.log`** with a
  rotating file handler (5 MB × 2).
* When a user uploads a file that exceeds **`MAX_UPLOAD_SIZE_MB`** a proper
  `413` JSON error is returned – the front-end relays the message.

---

## 5. Future extensions

* Progress updates via WebSocket (see *Roadmap G4*).
* Virus scan hook before saving the file.
* Per-user isolation once authentication lands.

# API Endpoint Testing Guide

This guide provides example `curl` commands for testing the API endpoints of The Podcaster API.

**Prerequisites:**
*   The FastAPI application should be running (e.g., via `docker-compose up` or directly with uvicorn).
*   Adjust `localhost:8000` if your application is running on a different host or port.
*   For `POST` requests with file uploads, ensure you have sample files (e.g., `test.mp3`) in the directory where you run the `curl` command.
*   Replace placeholders like `{session_id}`, `{job_id}`, and `{filename}` with actual values obtained from previous API calls.

## Health Check

### Check API Health
GET /api/health
curl -X GET http://localhost:8000/api/health

## Audio File Management

### 1. Upload Audio Files
POST /api/audio/upload
curl -X POST "http://localhost:8000/api/audio/upload"  -H "Content-Type: multipart/form-data"  -F "main_track=@path/to/your/main_audio.mp3"  -F "intro=@path/to/your/intro_audio.mp3"  -F "outro=@path/to/your/outro_audio.mp3"
# Note: 'intro' and 'outro' are optional.
# Expected response: JSON with "upload_session_id" and "saved_files". Save the session_id.

### 2. List Upload Sessions
GET /api/audio/uploads
curl -X GET http://localhost:8000/api/audio/uploads
# Expected response: JSON list of session_id strings.

### 3. List Files in an Upload Session
GET /api/audio/uploads/{session_id}
# Replace {session_id} with an actual session ID from the upload step.
curl -X GET http://localhost:8000/api/audio/uploads/your_session_id
# Expected response: JSON list of filenames in that session.

### 4. Download/Play an Original Uploaded File
GET /api/audio/uploads/{session_id}/{filename}
# Replace {session_id} and {filename} with actual values.
curl -X GET http://localhost:8000/api/audio/uploads/your_session_id/your_file.mp3 -o downloaded_original.mp3
# This will save the file. Browsers can often play directly from this URL.

### 5. Start Audio Processing
POST /api/audio/process/{session_id}
# Replace {session_id} with an actual session ID.
curl -X POST http://localhost:8000/api/audio/process/your_session_id
# Expected response: JSON with "job_id" and "message". Save the job_id.

### 6. Get Job Status
GET /api/audio/status/{job_id}
# Replace {job_id} with an actual job ID.
curl -X GET http://localhost:8000/api/audio/status/your_job_id
# Expected response: JSON with job status and "output_file_path" if completed.

### 7. Download Processed Audio File
GET /api/audio/download/{job_id}
# Replace {job_id} with a completed job ID.
curl -X GET http://localhost:8000/api/audio/download/your_job_id -o downloaded_processed.mp3
# This will save the file.

### 8. List All Processed Files
GET /api/audio/processed_files
curl -X GET http://localhost:8000/api/audio/processed_files
# Expected response: JSON list of processed file details.

### 9. Delete an Upload Session
DELETE /api/audio/uploads/{session_id}
# Replace {session_id} with an actual session ID.
curl -X DELETE http://localhost:8000/api/audio/uploads/your_session_id
# Expected response: 204 No Content on success.

### 10. Delete a Processed Audio File
DELETE /api/audio/processed_files/{job_id}
# Replace {job_id} with an actual job ID whose file you want to delete.
curl -X DELETE http://localhost:8000/api/audio/processed_files/your_job_id
# Expected response: 204 No Content on success.

## Output File Management (Generic Outputs)

### 1. List Output Files
GET /api/outputs
curl -X GET http://localhost:8000/api/outputs
# Expected response: JSON list of filenames in the OUTPUTS_DIR.
# Note: You need to manually place files in OUTPUTS_DIR for them to be listed,
# as there's no dedicated upload endpoint for this generic directory in this version.

### 2. Download/Play an Output File
GET /api/outputs/{filename}
# Replace {filename} with an actual filename from the outputs directory.
curl -X GET http://localhost:8000/api/outputs/your_output_file.txt -o downloaded_output.txt
# This will save the file.

### 3. Delete an Output File
DELETE /api/outputs/{filename}
# Replace {filename} with an actual filename from the outputs directory.
curl -X DELETE http://localhost:8000/api/outputs/your_output_file.txt
# Expected response: 204 No Content on success.

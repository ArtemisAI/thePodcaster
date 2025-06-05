# Netlify Deployment Notes

This document outlines specific considerations and changes made to deploy this application on Netlify.

## API Backend (Netlify Functions)

The FastAPI backend located in the `backend/` directory has been adapted to run as a Netlify Function. The entry point for this function is `netlify/functions/api.py`.

## File Uploads

**Important:** The original nginx configuration allowed for file uploads up to 2GB (`client_max_body_size 2g;`). Netlify Functions have significantly smaller request payload limits (typically around 6MB for synchronous invocations, or 4.5MB for binary data due to Base64 encoding).

This means that **direct uploads of files larger than this limit to the API endpoints will fail.**

To handle uploads of very large files (approaching or exceeding these limits), the application's frontend or client-side logic would need to be modified to:
1. Upload large files directly to a dedicated file storage service (e.g., AWS S3, Google Cloud Storage, Netlify Blobs if suitable for the use case).
2. The client would then make an API call to the Netlify Function, providing a reference (like a URL or ID) to the uploaded file for backend processing.

This is an architectural change from how the application might have operated with a traditional server setup. For the current Netlify deployment, API endpoints will be constrained by Netlify's function payload limits.

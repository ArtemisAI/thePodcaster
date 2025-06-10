# The Podcaster - Frontend

## Overview

This directory contains the frontend for "The Podcaster" application. It is a client-side application built using HTML, CSS, and vanilla JavaScript. Its primary purpose is to provide a user interface for:

*   Uploading main audio tracks, along with optional intro and outro segments.
*   Tracking the status of audio processing jobs (currently mocked, requires backend integration).
*   Accessing a media library of processed audio files (currently mocked, requires backend integration).

The application is designed to be simple, responsive, and user-friendly.

## Current Features

*   **Audio Upload:** Allows users to select a main audio file, and optional intro/outro files.
*   **Client-Side Validation:** Validates files before upload based on type (MP3, WAV). The allowed size is controlled by the backend via the ``MAX_UPLOAD_SIZE_MB`` environment variable (default: 500MB).
*   **Job Status View:** A dedicated view to display the status of processing jobs. (Note: Data is currently mocked and requires a backend to show real-time job statuses).
*   **Media Library View:** A view to browse and download processed media. (Note: Data is currently mocked and requires a backend).
*   **Responsive Design:** The user interface adapts to different screen sizes (mobile, tablet, desktop).
*   **Tooltips:** Helpful "question bubble" tooltips provide more information about specific fields and actions.
*   **Visual Feedback:** Loading spinners and status messages inform the user about ongoing operations.
*   **Accessibility:** Efforts have been made to ensure semantic HTML and ARIA attributes are used for better accessibility.

## Setup and Running

This is a static frontend application consisting of HTML, CSS, and JavaScript files. No build process is required.

**1. Serving Locally:**

To run the frontend locally, you can use any simple HTTP server. Here are a couple of examples:

*   **Using Python:**
    If you have Python installed, navigate to the `frontend` directory in your terminal and run:
    ```bash
    python -m http.server
    # For Python 2.x:
    # python -m SimpleHTTPServer
    ```
    This will typically serve the frontend at `http://localhost:8000`.

*   **Using Node.js `serve` package:**
    If you have Node.js and npm installed, you can use the `serve` package:
    ```bash
    npx serve .
    ```
    This will also serve the frontend, usually on a port like `http://localhost:3000` or `http://localhost:5000`.

**2. API Configuration:**

The frontend communicates with a backend API. The base URL for this API is defined in `frontend/script.js`:

```javascript
// frontend/script.js
const App = {
    API_BASE_URL: '/api',
    // ...
};
```

By default, it's set to `/api`. This assumes that in a production-like environment, the same web server serving the frontend will proxy requests starting with `/api/` to the backend service. If you are running the backend on a different domain or port during local development (e.g., backend on `http://localhost:8000` and frontend on `http://localhost:3000`), you might need to temporarily change `API_BASE_URL` to the full backend address (e.g., `http://localhost:8000/api`) and ensure the backend supports CORS (Cross-Origin Resource Sharing). For production, configuring a reverse proxy is the recommended approach (see Deployment section).

## Deployment

The frontend consists of static files (`index.html`, `style.css`, `script.js`) that can be served by any web server like Nginx, Apache, or cloud-based static hosting services (e.g., AWS S3 with CloudFront, Netlify, Vercel, GitHub Pages).

**Nginx Configuration Example:**

Below is a basic Nginx configuration example. This setup serves the frontend files and proxies API requests to a backend service running, for example, on `localhost:8000` (where the FastAPI backend might be).

```nginx
server {
    listen 80; # Or 443 for HTTPS
    server_name yourdomain.com; # Replace with your domain or IP

    # Root directory for frontend files
    root /path/to/your/frontend_files; # Replace with the actual path to index.html, style.css, script.js
    index index.html;

    # Serve static frontend files
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Reverse proxy for API requests
    # All requests to /api/... will be forwarded to the backend
    location /api/ {
        proxy_pass http://localhost:8000/api/; # Assuming backend is on port 8000
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Optional: If your backend uses WebSockets (e.g., for job status updates)
        # proxy_http_version 1.1;
        # proxy_set_header Upgrade $http_upgrade;
        # proxy_set_header Connection "upgrade";
    }

    # Optional: Add error pages, logging, SSL configuration, etc.
    # error_page 500 502 503 504 /50x.html;
    # location = /50x.html {
    //     root /usr/share/nginx/html;
    # }

    # access_log /var/log/nginx/frontend.access.log;
    # error_log /var/log/nginx/frontend.error.log;
}
```

**Key Nginx Configuration Points:**

*   `root`: Specifies the directory where your `index.html`, `style.css`, and `script.js` are located.
*   `location /`: Serves the static files. `try_files` ensures that direct requests to files are served, and any other path (like for client-side routing, though not used heavily in this simple version) falls back to `index.html`.
*   `location /api/`: This is crucial. It captures any request starting with `/api/` and forwards it to the backend service (defined by `proxy_pass`). The trailing slash in `proxy_pass http://localhost:8000/api/;` is important and means that a request to `/api/audio/upload` will be proxied to `http://localhost:8000/api/audio/upload`.

**Build Steps:**

Currently, this vanilla JS frontend does not have any build steps. The files can be deployed as-is.

## Backend Dependency

This frontend application is **not standalone**. It requires a backend service to handle file uploads, audio processing, job management, and provide data for the jobs list and media library.

Please refer to the main project README or the backend's specific documentation for instructions on setting up and running the backend API service. The frontend expects the backend to expose endpoints under the `/api` path as configured (e.g., `/api/audio/upload`, `/api/jobs`, etc.).

## Future Plans (Beyond Vanilla JS)

While the current vanilla JavaScript frontend provides core functionality, a more advanced version is planned for the future. This future iteration is expected to be built using a modern JavaScript framework/library such as **React with TypeScript, powered by Vite** for an enhanced development experience and more complex UI capabilities.

The planned structure for this future version might look like:

```
frontend
├── public/           # Static assets, favicon, cover-art placeholders
└── src/
    ├── components/   # Reusable widgets
    ├── pages/        # Route-level components – Library, Editor, Jobs, Settings
    ├── hooks/        # Custom React hooks (e.g. useJobStream)
    ├── api/          # Thin client around the backend REST endpoints
    └── App.tsx
```
This would involve embedding or interfacing with audio editing libraries like AudioMass directly within the React component structure.
```

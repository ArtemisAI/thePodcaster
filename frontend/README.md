# Front-end (phase 2)

This directory will eventually host the React (or equivalent) codebase that wraps the AudioMass editor and communicates with the FastAPI backend.

Planned structure (subject to change):

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

We will pick **Vite + React + TypeScript** for fast DX, then embed the AudioMass source under `src/vendor/audiomass` and expose it as a React component.

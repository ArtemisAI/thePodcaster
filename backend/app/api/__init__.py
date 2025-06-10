# Router aggregator – import each route module here and expose ``api_router``
# for convenient inclusion in the FastAPI app.

from fastapi import APIRouter

from . import (
    routes_audio,
    routes_jobs,
    routes_library,
    routes_llm,
    routes_outputs,
    routes_publish,
    routes_transcription,
    routes_video,
)


api_router = APIRouter()
api_router.include_router(routes_audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(routes_llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(routes_transcription.router, prefix="/transcription", tags=["transcription"])
api_router.include_router(routes_publish.router, prefix="/publish", tags=["publish"])
api_router.include_router(routes_outputs.router, prefix="/outputs", tags=["outputs"])
api_router.include_router(routes_video.router, prefix="/video", tags=["video"])
api_router.include_router(routes_library.router, prefix="/library", tags=["library"])
api_router.include_router(routes_jobs.router, prefix="/jobs", tags=["jobs"])

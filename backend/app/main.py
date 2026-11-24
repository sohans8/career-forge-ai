import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.models.schemas import HealthResponse
from backend.app.routes import platform
from backend.app.routes.recommendation import router as recommendation_router

log = logging.getLogger("career_forge")

app = FastAPI(
    title="Career Forge AI API",
    description="AI career platform for Indian students: roadmaps, colleges, AI mentor, resume analyzer and guidance.",
    version="2.0.0",
)

_origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(recommendation_router)
for r in (platform.roadmaps, platform.colleges, platform.mentor, platform.resume, platform.guidance, platform.system):
    app.include_router(r)


@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Career Forge AI API", "docs": "/docs"}


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return {"status": "ok"}

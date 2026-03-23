"""FastAPI application entry point for the Zip2Job API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from capstone_project_team_5.api.routes import (
    auth,
    consent,
    educations,
    health,
    portfolio,
    projects,
    resumes,
    skills,
    users,
    work_experiences,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize resources on startup and clean up on shutdown."""
    from capstone_project_team_5.data.db import init_db

    init_db()
    yield


app = FastAPI(
    title="Zip2Job API",
    description="API for analyzing project artifacts and generating portfolio content",
    version="0.1.0",
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(consent.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(skills.global_router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(work_experiences.router, prefix="/api")
app.include_router(educations.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")

# Serve the built frontend when SERVE_FRONTEND is set (Railway production).
# Must be mounted LAST so /api/* and /health routes take precedence.
if os.getenv("SERVE_FRONTEND"):
    from fastapi.staticfiles import StaticFiles

    _frontend_dir = os.getenv("FRONTEND_DIR", "./frontend_dist")
    if os.path.isdir(_frontend_dir):
        app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


def main() -> None:
    """Start the API server."""
    import uvicorn

    env = os.getenv("ENVIRONMENT", "development")
    port = int(os.getenv("PORT", "8000"))
    reload = env == "development"
    workers = int(os.getenv("WEB_CONCURRENCY", "1"))

    uvicorn.run(
        "capstone_project_team_5.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        workers=1 if reload else workers,
    )


if __name__ == "__main__":
    main()

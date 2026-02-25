"""FastAPI application entry point for the Zip2Job API."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from capstone_project_team_5.api.routes import (
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
from capstone_project_team_5.api.routes.skills import global_router as skills_global_router

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(consent.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(skills_global_router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(work_experiences.router, prefix="/api")
app.include_router(educations.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")


def main() -> None:
    """Start the development server."""
    import uvicorn

    uvicorn.run(
        "capstone_project_team_5.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()

"""Pydantic schemas for project API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectSummary(BaseModel):
    """Public-facing project summary for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rel_path: str
    file_count: int
    has_git_repo: bool
    is_collaborative: bool
    thumbnail_url: str | None
    importance_rank: int | None
    importance_score: float | None
    created_at: datetime
    updated_at: datetime


class ProjectUploadResponse(BaseModel):
    """Response schema for zip upload endpoint."""

    upload_id: int
    filename: str
    size_bytes: int
    file_count: int
    created_at: datetime
    projects: list[ProjectSummary]


class ProjectUpdateRequest(BaseModel):
    """Fields allowed to be updated for a project."""

    name: str | None = None
    rel_path: str | None = None
    thumbnail_url: str | None = None
    importance_rank: int | None = None
    importance_score: float | None = None

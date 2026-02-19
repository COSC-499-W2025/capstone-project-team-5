"""Pydantic schemas for resume API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResumeProjectResponse(BaseModel):
    """Response schema for a resume project entry."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_id: int
    project_id: int
    project_name: str
    rel_path: str
    title: str | None = None
    description: str | None = None
    analysis_snapshot: list[str] = []
    bullet_points: list[str] = []
    created_at: datetime
    updated_at: datetime


class ResumeProjectCreateRequest(BaseModel):
    """Request schema for creating/upserting a resume project entry."""

    project_id: int = Field(..., description="ID of the project to attach")
    title: str = Field(..., description="Custom title for the resume entry")
    description: str = Field("", description="Custom description (e.g. tech stack summary)")
    bullet_points: list[str] = Field(default_factory=list, description="Resume bullet points")
    analysis_snapshot: list[str] = Field(default_factory=list, description="Skills/tools snapshot")


class ResumeProjectUpdateRequest(BaseModel):
    """Request schema for partially updating a resume project entry.

    All fields are optional; only provided fields are updated.
    """

    title: str | None = Field(None, description="Custom title")
    description: str | None = Field(None, description="Custom description")
    bullet_points: list[str] | None = Field(None, description="Resume bullet points")
    analysis_snapshot: list[str] | None = Field(None, description="Skills/tools snapshot")


class ResumeGenerateRequest(BaseModel):
    """Request schema for generating a PDF resume."""

    template_name: str = Field("jake", description="LaTeX template identifier")

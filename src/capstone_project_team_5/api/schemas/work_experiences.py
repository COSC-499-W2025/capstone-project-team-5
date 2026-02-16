"""Pydantic schemas for work experience API endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkExperienceResponse(BaseModel):
    """Response schema for work experience data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    company: str
    title: str
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    bullets: str | None = None
    is_current: bool = False
    rank: int = 0
    updated_at: datetime


class WorkExperienceCreateRequest(BaseModel):
    """Request schema for creating a work experience entry."""

    company: str = Field(..., description="Company or organization name")
    title: str = Field(..., description="Job title or position")
    location: str | None = Field(None, description="Job location")
    start_date: date | None = Field(None, description="Start date (ISO format)")
    end_date: date | None = Field(None, description="End date (ISO format, None if current)")
    description: str | None = Field(None, description="Brief role description")
    bullets: str | None = Field(None, description="JSON array of bullet points as string")
    is_current: bool = Field(False, description="Whether this is the current job")
    rank: int = Field(0, description="Display ordering (lower = higher priority)")


class WorkExperienceUpdateRequest(BaseModel):
    """Request schema for updating a work experience entry.

    All fields are optional; only provided fields are updated.
    """

    company: str | None = Field(None, description="Company or organization name")
    title: str | None = Field(None, description="Job title or position")
    location: str | None = Field(None, description="Job location")
    start_date: date | None = Field(None, description="Start date (ISO format)")
    end_date: date | None = Field(None, description="End date (ISO format)")
    description: str | None = Field(None, description="Brief role description")
    bullets: str | None = Field(None, description="JSON array of bullet points as string")
    is_current: bool | None = Field(None, description="Whether this is the current job")
    rank: int | None = Field(None, description="Display ordering (lower = higher priority)")

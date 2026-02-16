"""Pydantic schemas for education API endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class EducationResponse(BaseModel):
    """Response schema for education data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    institution: str
    degree: str
    field_of_study: str | None = None
    gpa: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    achievements: str | None = None
    is_current: bool = False
    rank: int = 0
    updated_at: datetime


class EducationCreateRequest(BaseModel):
    """Request schema for creating an education entry."""

    institution: str = Field(..., description="School or university name")
    degree: str = Field(..., description="Degree type (e.g., Bachelor of Science)")
    field_of_study: str | None = Field(None, description="Major or field of study")
    gpa: float | None = Field(None, description="Grade point average (0.0-5.0)")
    start_date: date | None = Field(None, description="Start date (ISO format)")
    end_date: date | None = Field(None, description="End date (ISO format, None if current)")
    achievements: str | None = Field(None, description="JSON array of achievements as string")
    is_current: bool = Field(False, description="Whether currently enrolled")
    rank: int = Field(0, description="Display ordering (lower = higher priority)")


class EducationUpdateRequest(BaseModel):
    """Request schema for updating an education entry.

    All fields are optional; only provided fields are updated.
    """

    institution: str | None = Field(None, description="School or university name")
    degree: str | None = Field(None, description="Degree type")
    field_of_study: str | None = Field(None, description="Major or field of study")
    gpa: float | None = Field(None, description="Grade point average (0.0-5.0)")
    start_date: date | None = Field(None, description="Start date (ISO format)")
    end_date: date | None = Field(None, description="End date (ISO format)")
    achievements: str | None = Field(None, description="JSON array of achievements as string")
    is_current: bool | None = Field(None, description="Whether currently enrolled")
    rank: int | None = Field(None, description="Display ordering (lower = higher priority)")

"""Pydantic schemas for portfolio editing endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PortfolioEditRequest(BaseModel):
    """Request body for creating or updating a portfolio item."""

    username: str
    project_id: int
    markdown: str
    title: str | None = None
    source_analysis_id: int | None = None
    is_showcase: bool = False


class PortfolioItemResponse(BaseModel):
    """Response model for a portfolio item."""

    id: int
    project_id: int | None
    title: str
    markdown: str
    is_user_edited: bool
    is_showcase: bool
    source_analysis_id: int | None
    created_at: datetime
    updated_at: datetime

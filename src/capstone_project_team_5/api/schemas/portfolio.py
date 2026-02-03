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
    portfolio_id: int | None = None


class PortfolioItemResponse(BaseModel):
    """Response model for a portfolio item."""

    id: int
    project_id: int | None
    title: str
    markdown: str
    is_user_edited: bool
    source_analysis_id: int | None
    portfolio_id: int | None
    created_at: datetime
    updated_at: datetime


class PortfolioCreateRequest(BaseModel):
    """Request body for creating a new portfolio for a user."""

    username: str
    name: str


class PortfolioResponse(BaseModel):
    """Response model for a logical portfolio grouping."""

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class PortfolioAddItemRequest(BaseModel):
    """Request body for adding an existing project into a portfolio.

    This creates (or reuses) a PortfolioItem so that the project appears
    in the specified portfolio, even if the user has not edited content yet.
    """

    username: str
    project_id: int
    source_analysis_id: int | None = None

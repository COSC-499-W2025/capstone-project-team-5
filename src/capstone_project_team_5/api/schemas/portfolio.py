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
    is_text_block: bool = False
    source_analysis_id: int | None
    portfolio_id: int | None
    created_at: datetime
    updated_at: datetime


class PortfolioTextBlockRequest(BaseModel):
    """Request body for creating or updating a text block in a portfolio."""

    title: str = ""
    markdown: str = ""


class PortfolioItemUpdateRequest(BaseModel):
    """Request body for updating a portfolio item's content."""

    title: str | None = None
    markdown: str | None = None


class PortfolioReorderRequest(BaseModel):
    """Ordered list of item IDs defining the new display order."""

    item_ids: list[int]


class PortfolioCreateRequest(BaseModel):
    """Request body for creating a new portfolio for a user."""

    username: str
    name: str


class PortfolioResponse(BaseModel):
    """Response model for a logical portfolio grouping."""

    id: int
    name: str
    share_token: str | None = None
    template: str = "grid"
    color_theme: str = "dark"
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class PortfolioUpdateRequest(BaseModel):
    """Request body for updating portfolio metadata (template, color_theme, description)."""

    template: str | None = None
    color_theme: str | None = None
    description: str | None = None


class PortfolioShareResponse(BaseModel):
    """Response after generating a share link for a portfolio."""

    share_token: str


class PublicPortfolioResponse(BaseModel):
    """Public-facing portfolio view returned by the shared link endpoint."""

    id: int
    name: str
    owner: str
    share_token: str
    items: list[PortfolioItemResponse]


class PortfolioAddItemRequest(BaseModel):
    """Request body for adding an existing project into a portfolio.

    This creates (or reuses) a PortfolioItem so that the project appears
    in the specified portfolio, even if the user has not edited content yet.
    """

    username: str
    project_id: int
    source_analysis_id: int | None = None

"""Shared Pydantic schemas for API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Default pagination values
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(description="Total number of items available")
    limit: int = Field(description="Maximum number of items returned")
    offset: int = Field(description="Number of items skipped")
    has_more: bool = Field(description="Whether there are more items available")

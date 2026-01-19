"""Pydantic schemas for skills API responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from capstone_project_team_5.constants.skill_detection_constants import SkillType

# Default pagination values
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


class SkillResponse(BaseModel):
    """Public-facing skill schema for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    skill_type: SkillType


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(description="Total number of items available")
    limit: int = Field(description="Maximum number of items returned")
    offset: int = Field(description="Number of items skipped")
    has_more: bool = Field(description="Whether there are more items available")


class PaginatedSkillsResponse(BaseModel):
    """Paginated list of skills."""

    items: list[SkillResponse]
    pagination: PaginationMeta


class ProjectSkillsResponse(BaseModel):
    """Skills grouped by type for a project."""

    project_id: int
    tools: list[SkillResponse]
    practices: list[SkillResponse]
    tools_count: int = Field(description="Total number of tools for this project")
    practices_count: int = Field(description="Total number of practices for this project")

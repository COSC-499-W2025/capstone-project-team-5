"""Pydantic schemas for skills API responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from capstone_project_team_5.api.schemas.common import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    PaginationMeta,
)
from capstone_project_team_5.constants.skill_detection_constants import SkillType

# Re-export for backwards compatibility
__all__ = ["DEFAULT_LIMIT", "MAX_LIMIT", "PaginationMeta"]


class SkillResponse(BaseModel):
    """Public-facing skill schema for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    skill_type: SkillType


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

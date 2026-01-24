"""Pydantic schemas for consent API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConsentRecordSummary(BaseModel):
    """Public-facing consent record summary for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    consent_given: bool
    use_external_services: bool
    external_services: dict[str, Any]
    default_ignore_patterns: list[str]
    created_at: datetime


class ConsentCreateRequest(BaseModel):
    """Request schema for creating a consent record."""

    user_id: int | None = Field(
        None,
        description="Optional user ID to associate with this consent record",
    )
    consent_given: bool = Field(
        ...,
        description="Whether the user agreed to main file access consent",
    )
    use_external_services: bool = Field(
        False,
        description="Whether the user agreed to external service integration",
    )
    external_services: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON mapping of service names to configuration objects",
    )
    default_ignore_patterns: list[str] = Field(
        default_factory=list,
        description="List of file/folder patterns to ignore during analysis",
    )


class ConsentUpdateRequest(BaseModel):
    """Request schema for updating consent preferences."""

    consent_given: bool | None = Field(
        None,
        description="Whether the user agrees to main file access consent",
    )
    use_external_services: bool | None = Field(
        None,
        description="Whether the user agrees to external service integration",
    )
    external_services: dict[str, Any] | None = Field(
        None,
        description="JSON mapping of service names to configuration objects",
    )
    default_ignore_patterns: list[str] | None = Field(
        None,
        description="List of file/folder patterns to ignore during analysis",
    )


class AvailableServicesResponse(BaseModel):
    """Response schema for available external services."""

    external_services: list[str] = Field(
        ...,
        description="List of available external service names",
    )
    ai_models: list[str] = Field(
        ...,
        description="List of available AI model names",
    )
    common_ignore_patterns: list[str] = Field(
        ...,
        description="List of commonly used ignore patterns",
    )


class LLMConfigResponse(BaseModel):
    """Response schema for LLM configuration status."""

    is_allowed: bool = Field(
        ...,
        description="Whether LLM usage is allowed based on user consent",
    )
    model_preferences: list[str] = Field(
        default_factory=list,
        description="User's LLM model preferences in priority order",
    )

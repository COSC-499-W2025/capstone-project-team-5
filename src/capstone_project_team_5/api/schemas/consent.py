"""Pydantic schemas for consent API endpoints.

Supports four endpoints:
- GET  /available-services  — lists services, models, ignore patterns
- POST /consent             — upsert consent settings
- GET  /consent/latest      — current consent settings
- GET  /consent/llm/config  — LLM allowance check
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConsentRecordSummary(BaseModel):
    """Public-facing consent record returned by most endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    consent_given: bool
    use_external_services: bool
    external_services: dict[str, Any]
    default_ignore_patterns: list[str]
    created_at: datetime


class ConsentUpsertRequest(BaseModel):
    """Body for ``POST /api/consent`` (create-or-replace).

    The owning user is determined by the ``X-Username`` header,
    not by a field in the body.  Omitting the header creates a
    global (anonymous) record.
    """

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


class AvailableServicesResponse(BaseModel):
    """Response for ``GET /api/consent/available-services``."""

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
    """Response for ``GET /api/consent/llm/config``."""

    is_allowed: bool = Field(
        ...,
        description="Whether LLM usage is allowed based on user consent",
    )
    model_preferences: list[str] = Field(
        default_factory=list,
        description="User's LLM model preferences in priority order",
    )

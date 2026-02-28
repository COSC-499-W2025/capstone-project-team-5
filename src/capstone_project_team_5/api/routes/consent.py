"""Consent routes for the API.

Provides four endpoints for managing user privacy consent:

- ``GET  /available-services``  — list services, AI models, and ignore patterns
- ``POST /consent``             — create or update (upsert) consent settings
- ``GET  /consent/latest``      — retrieve current consent settings
- ``GET  /consent/llm/config``  — check whether LLM usage is permitted

Authentication uses the shared ``X-Username`` header (consistent with the
rest of the API).  Consent endpoints accept the header **optionally** —
omitting it addresses *global* (anonymous) consent records.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from capstone_project_team_5.api.dependencies import get_optional_username
from capstone_project_team_5.api.schemas.consent import (
    AvailableServicesResponse,
    ConsentRecordSummary,
    ConsentUpsertRequest,
    LLMConfigResponse,
)
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ConsentRecord, User

router = APIRouter(prefix="/consent", tags=["consent"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_user_id(session: Session, username: str | None) -> int | None:
    """Look up the numeric user ID for *username*.

    Returns ``None`` when *username* is ``None`` (global / anonymous).

    Raises:
        HTTPException: 404 if *username* is provided but does not exist.
    """
    if username is None:
        return None
    user = session.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )
    return user.id


def _get_latest_record(
    session: Session,
    user_id: int | None,
    *,
    fallback_to_global: bool = True,
) -> ConsentRecord | None:
    """Return the newest consent record for *user_id*.

    When *fallback_to_global* is ``True`` and no user-specific record exists,
    the latest global record (``user_id IS NULL``) is returned instead.
    """
    if user_id is not None:
        record = (
            session.query(ConsentRecord)
            .filter(ConsentRecord.user_id == user_id)
            .order_by(desc(ConsentRecord.created_at))
            .first()
        )
        if record is not None or not fallback_to_global:
            return record
        # Fall through to global lookup

    return (
        session.query(ConsentRecord)
        .filter(ConsentRecord.user_id.is_(None))
        .order_by(desc(ConsentRecord.created_at))
        .first()
    )


def _to_summary(record: ConsentRecord) -> ConsentRecordSummary:
    """Convert an ORM ``ConsentRecord`` to its Pydantic response model."""
    return ConsentRecordSummary(
        id=record.id,
        user_id=record.user_id,
        consent_given=record.consent_given,
        use_external_services=record.use_external_services,
        external_services=record.external_services,
        default_ignore_patterns=record.default_ignore_patterns,
        created_at=record.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/available-services", response_model=AvailableServicesResponse)
def get_available_services() -> AvailableServicesResponse:
    """List available external services, AI models, and common ignore patterns.

    No authentication required.
    """
    return AvailableServicesResponse(
        external_services=ConsentTool.AVAILABLE_EXTERNAL_SERVICES,
        ai_models=ConsentTool.AVAILABLE_AI_MODELS,
        common_ignore_patterns=ConsentTool.COMMON_IGNORE_PATTERNS,
    )


@router.post("", response_model=ConsentRecordSummary)
def upsert_consent(
    body: ConsentUpsertRequest,
    current_username: Annotated[str | None, Depends(get_optional_username)],
) -> ConsentRecordSummary:
    """Create or replace the current consent settings.

    * **Authenticated** (``X-Username`` header) → user-specific consent.
    * **Anonymous** (no header) → global consent.

    If a record already exists for the identified scope it is updated
    in place; otherwise a new record is created.
    """
    with get_session() as session:
        user_id = _resolve_user_id(session, current_username)

        existing = _get_latest_record(session, user_id, fallback_to_global=False)

        if existing is not None:
            existing.consent_given = body.consent_given
            existing.use_external_services = body.use_external_services
            existing.external_services = body.external_services
            existing.default_ignore_patterns = body.default_ignore_patterns
            session.flush()
            session.refresh(existing)
            return _to_summary(existing)

        record = ConsentRecord(
            user_id=user_id,
            consent_given=body.consent_given,
            use_external_services=body.use_external_services,
            external_services=body.external_services,
            default_ignore_patterns=body.default_ignore_patterns,
        )
        session.add(record)
        session.flush()
        session.refresh(record)
        return _to_summary(record)


@router.get("/latest", response_model=ConsentRecordSummary)
def get_latest_consent(
    current_username: Annotated[str | None, Depends(get_optional_username)],
    fallback_to_global: Annotated[
        bool,
        Query(
            description="Fall back to global record when no user-specific record exists",
        ),
    ] = True,
) -> ConsentRecordSummary:
    """Return the current consent settings.

    * **Authenticated** → latest record for that user (with optional
      global fallback).
    * **Anonymous** → latest global record.
    """
    with get_session() as session:
        user_id = _resolve_user_id(session, current_username)
        record = _get_latest_record(session, user_id, fallback_to_global=fallback_to_global)

        if record is None:
            scope = f"user '{current_username}'" if current_username else "global"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No consent record found for {scope}",
            )

        return _to_summary(record)


@router.get("/llm/config", response_model=LLMConfigResponse)
def get_llm_config(
    current_username: Annotated[str | None, Depends(get_optional_username)],
) -> LLMConfigResponse:
    """Check whether LLM / AI usage is permitted under current consent."""
    consent_tool = ConsentTool()

    with get_session() as session:
        user_id = _resolve_user_id(session, current_username)
        record = _get_latest_record(session, user_id, fallback_to_global=True)

        if record is None:
            return LLMConfigResponse(is_allowed=False, model_preferences=[])

        consent_tool.use_external_services = record.use_external_services
        consent_tool.external_services = record.external_services or {}

        return LLMConfigResponse(
            is_allowed=consent_tool.is_llm_allowed(),
            model_preferences=consent_tool.get_llm_model_preferences(),
        )

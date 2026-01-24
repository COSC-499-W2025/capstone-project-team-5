"""Consent routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import desc

from capstone_project_team_5.api.schemas.consent import (
    AvailableServicesResponse,
    ConsentCreateRequest,
    ConsentRecordSummary,
    ConsentUpdateRequest,
    LLMConfigResponse,
)
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ConsentRecord, User

router = APIRouter(prefix="/consent", tags=["consent"])


def _consent_record_to_summary(record: ConsentRecord) -> ConsentRecordSummary:
    """Convert a ConsentRecord ORM model to a Pydantic schema."""
    return ConsentRecordSummary(
        id=record.id,
        user_id=record.user_id,
        consent_given=record.consent_given,
        use_external_services=record.use_external_services,
        external_services=record.external_services,
        default_ignore_patterns=record.default_ignore_patterns,
        created_at=record.created_at,
    )


@router.get("/available-services", response_model=AvailableServicesResponse)
def get_available_services() -> AvailableServicesResponse:
    """Get lists of available external services, AI models, and common ignore patterns.

    Returns:
        AvailableServicesResponse: Lists of available services and patterns.
    """
    return AvailableServicesResponse(
        external_services=ConsentTool.AVAILABLE_EXTERNAL_SERVICES,
        ai_models=ConsentTool.AVAILABLE_AI_MODELS,
        common_ignore_patterns=ConsentTool.COMMON_IGNORE_PATTERNS,
    )


@router.post(
    "",
    response_model=ConsentRecordSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_consent_record(
    consent_request: ConsentCreateRequest,
) -> ConsentRecordSummary:
    """Create a new consent record.

    Args:
        consent_request: Consent configuration data.

    Returns:
        ConsentRecordSummary: The created consent record.

    Raises:
        HTTPException: If user_id is provided but user doesn't exist.
    """
    with get_session() as session:
        # Validate user_id if provided
        if consent_request.user_id is not None:
            user = session.query(User).filter(User.id == consent_request.user_id).first()
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {consent_request.user_id} not found",
                )

        # Create new consent record
        new_record = ConsentRecord(
            user_id=consent_request.user_id,
            consent_given=consent_request.consent_given,
            use_external_services=consent_request.use_external_services,
            external_services=consent_request.external_services,
            default_ignore_patterns=consent_request.default_ignore_patterns,
        )
        session.add(new_record)
        session.flush()  # Get the ID without committing
        session.refresh(new_record)

        return _consent_record_to_summary(new_record)


@router.get("", response_model=list[ConsentRecordSummary])
def get_consent_records(
    user_id: Annotated[int | None, Query(description="Filter by user ID")] = None,
    limit: Annotated[
        int, Query(description="Maximum number of records to return", ge=1, le=100)
    ] = 10,
) -> list[ConsentRecordSummary]:
    """Get consent records, optionally filtered by user.

    Args:
        user_id: Optional user ID to filter records.
        limit: Maximum number of records to return (1-100).

    Returns:
        list[ConsentRecordSummary]: List of consent records ordered by creation date (newest first).
    """
    with get_session() as session:
        query = session.query(ConsentRecord)

        if user_id is not None:
            query = query.filter(ConsentRecord.user_id == user_id)

        records = query.order_by(desc(ConsentRecord.created_at)).limit(limit).all()

        return [_consent_record_to_summary(record) for record in records]


@router.get("/latest", response_model=ConsentRecordSummary)
def get_latest_consent_record(
    user_id: Annotated[int | None, Query(description="Filter by user ID")] = None,
) -> ConsentRecordSummary:
    """Get the most recent consent record, optionally for a specific user.

    If user_id is provided, returns the latest record for that user.
    Otherwise, returns the latest global (no user_id) record.

    Args:
        user_id: Optional user ID to get latest record for.

    Returns:
        ConsentRecordSummary: The most recent consent record.

    Raises:
        HTTPException: If no consent record is found.
    """
    with get_session() as session:
        query = session.query(ConsentRecord)

        if user_id is not None:
            query = query.filter(ConsentRecord.user_id == user_id)
        else:
            query = query.filter(ConsentRecord.user_id.is_(None))

        record = query.order_by(desc(ConsentRecord.created_at)).first()

        if record is None:
            filter_msg = f"for user_id={user_id}" if user_id is not None else "without user_id"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No consent record found {filter_msg}",
            )

        return _consent_record_to_summary(record)


@router.get("/{consent_id}", response_model=ConsentRecordSummary)
def get_consent_record(
    consent_id: Annotated[int, Path(description="Consent record ID")],
) -> ConsentRecordSummary:
    """Get a specific consent record by ID.

    Args:
        consent_id: The ID of the consent record to retrieve.

    Returns:
        ConsentRecordSummary: The consent record.

    Raises:
        HTTPException: If the consent record is not found.
    """
    with get_session() as session:
        record = session.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consent record with id {consent_id} not found",
            )

        return _consent_record_to_summary(record)


@router.patch("/{consent_id}", response_model=ConsentRecordSummary)
def update_consent_record(
    consent_id: Annotated[int, Path(description="Consent record ID")],
    update_request: ConsentUpdateRequest,
) -> ConsentRecordSummary:
    """Update an existing consent record.

    Note: This updates the existing record rather than creating a new one.
    For tracking consent history, consider creating a new record instead.

    Args:
        consent_id: The ID of the consent record to update.
        update_request: Fields to update.

    Returns:
        ConsentRecordSummary: The updated consent record.

    Raises:
        HTTPException: If the consent record is not found.
    """
    with get_session() as session:
        record = session.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consent record with id {consent_id} not found",
            )

        # Update only provided fields
        if update_request.consent_given is not None:
            record.consent_given = update_request.consent_given
        if update_request.use_external_services is not None:
            record.use_external_services = update_request.use_external_services
        if update_request.external_services is not None:
            record.external_services = update_request.external_services
        if update_request.default_ignore_patterns is not None:
            record.default_ignore_patterns = update_request.default_ignore_patterns

        session.flush()
        session.refresh(record)

        return _consent_record_to_summary(record)


@router.delete("/{consent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consent_record(
    consent_id: Annotated[int, Path(description="Consent record ID")],
) -> None:
    """Delete a consent record.

    Args:
        consent_id: The ID of the consent record to delete.

    Raises:
        HTTPException: If the consent record is not found.
    """
    with get_session() as session:
        record = session.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consent record with id {consent_id} not found",
            )

        session.delete(record)


@router.get("/llm/config", response_model=LLMConfigResponse)
def get_llm_config(
    user_id: Annotated[int | None, Query(description="User ID to check LLM config for")] = None,
) -> LLMConfigResponse:
    """Check LLM configuration status based on the latest consent record.

    Args:
        user_id: Optional user ID to check LLM config for.

    Returns:
        LLMConfigResponse: LLM configuration status and preferences.
    """
    # Load the latest consent record for the user
    consent_tool = ConsentTool()

    with get_session() as session:
        query = session.query(ConsentRecord)

        if user_id is not None:
            # Try user-specific record first
            query = query.filter(ConsentRecord.user_id == user_id)
            record = query.order_by(desc(ConsentRecord.created_at)).first()

            # Fall back to global record if no user-specific record
            if record is None:
                query = session.query(ConsentRecord).filter(ConsentRecord.user_id.is_(None))
                record = query.order_by(desc(ConsentRecord.created_at)).first()
        else:
            # Get global record
            query = query.filter(ConsentRecord.user_id.is_(None))
            record = query.order_by(desc(ConsentRecord.created_at)).first()

        if record is None:
            # No consent record found, return defaults
            return LLMConfigResponse(
                is_allowed=False,
                model_preferences=[],
            )

        # Load consent data into tool
        consent_tool.use_external_services = record.use_external_services
        consent_tool.external_services = record.external_services or {}

        return LLMConfigResponse(
            is_allowed=consent_tool.is_llm_allowed(),
            model_preferences=consent_tool.get_llm_model_preferences(),
        )

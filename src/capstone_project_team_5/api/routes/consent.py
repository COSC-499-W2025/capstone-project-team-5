"""Consent routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

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


def get_current_user(
    x_user_id: Annotated[
        int | None,
        Header(
            description=(
                "Current user ID. In production, this should be extracted "
                "from authenticated session."
            )
        ),
    ] = None,
) -> int | None:
    """Get the current user from request context.

    NOTE: This is a simplified implementation using a header.
    In production, this should:
    - Extract user ID from authenticated session/JWT token
    - Validate the session is active and valid
    - Raise 401 if authentication is missing or invalid

    Args:
        x_user_id: User ID from X-User-Id header (temporary mechanism).

    Returns:
        int | None: The current user ID, or None for anonymous/system operations.
    """
    return x_user_id


def _verify_record_ownership(
    record: ConsentRecord,
    current_user_id: int | None,
) -> None:
    """Verify that the current user owns the consent record.

    Args:
        record: The consent record to verify.
        current_user_id: The current user's ID.

    Raises:
        HTTPException: If the user doesn't own the record (403 Forbidden).
    """
    # Allow access to global records (user_id is None) by anyone
    if record.user_id is None:
        return

    # For user-specific records, verify ownership
    if record.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this consent record",
        )


def _get_latest_consent_record(
    session: Session,
    user_id: int | None,
    fallback_to_global: bool = True,
) -> ConsentRecord | None:
    """Retrieve the latest consent record for a user with optional global fallback.

    This helper consolidates the duplicate logic found in get_latest_consent_record
    and get_llm_config endpoints.

    Args:
        session: Database session.
        user_id: User ID to query for, or None for global records.
        fallback_to_global: If True and no user-specific record is found,
            try to retrieve a global record (user_id is None).

    Returns:
        ConsentRecord | None: The latest consent record, or None if not found.
    """
    query = session.query(ConsentRecord)

    if user_id is not None:
        # Try user-specific record first
        query = query.filter(ConsentRecord.user_id == user_id)
        record = query.order_by(desc(ConsentRecord.created_at)).first()

        # Fall back to global record if requested and no user-specific record
        if record is None and fallback_to_global:
            query = session.query(ConsentRecord).filter(ConsentRecord.user_id.is_(None))
            record = query.order_by(desc(ConsentRecord.created_at)).first()
            return record

        return record
    else:
        # Get global record
        query = query.filter(ConsentRecord.user_id.is_(None))
        return query.order_by(desc(ConsentRecord.created_at)).first()


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
    current_user_id: Annotated[int | None, Depends(get_current_user)],
) -> ConsentRecordSummary:
    """Create a new consent record for the current user.

    Args:
        consent_request: Consent configuration data.
        current_user_id: Current authenticated user ID from dependency.

    Returns:
        ConsentRecordSummary: The created consent record.

    Raises:
        HTTPException: If trying to create record for different user (403),
            or if user doesn't exist (404).
    """
    with get_session() as session:
        # Use current_user_id instead of client-provided user_id for security
        # Only allow creating records for yourself or global records
        target_user_id = consent_request.user_id

        if target_user_id is not None:
            # Verify the user is creating a record for themselves
            if target_user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only create consent records for yourself",
                )

            # Validate user exists
            user = session.query(User).filter(User.id == target_user_id).first()
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {target_user_id} not found",
                )

        # Create new consent record
        new_record = ConsentRecord(
            user_id=target_user_id,
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
    current_user_id: Annotated[int | None, Depends(get_current_user)],
    include_global: Annotated[
        bool, Query(description="Include global (non-user-specific) records")
    ] = True,
    limit: Annotated[
        int, Query(description="Maximum number of records to return", ge=1, le=100)
    ] = 10,
) -> list[ConsentRecordSummary]:
    """Get consent records for the current user.

    Returns records owned by the current user, and optionally global records.

    Args:
        current_user_id: Current authenticated user ID from dependency.
        include_global: Whether to include global records (user_id is None).
        limit: Maximum number of records to return (1-100).

    Returns:
        list[ConsentRecordSummary]: List of consent records ordered by creation date (newest first).
    """
    with get_session() as session:
        query = session.query(ConsentRecord)

        # Filter to current user's records and optionally global records
        if current_user_id is not None:
            if include_global:
                query = query.filter(
                    (ConsentRecord.user_id == current_user_id) | (ConsentRecord.user_id.is_(None))
                )
            else:
                query = query.filter(ConsentRecord.user_id == current_user_id)
        else:
            # Anonymous user can only see global records
            query = query.filter(ConsentRecord.user_id.is_(None))

        records = query.order_by(desc(ConsentRecord.created_at)).limit(limit).all()

        return [_consent_record_to_summary(record) for record in records]


@router.get("/latest", response_model=ConsentRecordSummary)
def get_latest_consent_record(
    current_user_id: Annotated[int | None, Depends(get_current_user)],
    fallback_to_global: Annotated[
        bool,
        Query(description="If no user-specific record exists, fallback to global record"),
    ] = True,
) -> ConsentRecordSummary:
    """Get the most recent consent record for the current user.

    Returns the latest record for the current user. If fallback_to_global is True
    and no user-specific record exists, returns the latest global record.

    Args:
        current_user_id: Current authenticated user ID from dependency.
        fallback_to_global: Whether to fall back to global record if no user record exists.

    Returns:
        ConsentRecordSummary: The most recent consent record.

    Raises:
        HTTPException: If no consent record is found.
    """
    with get_session() as session:
        record = _get_latest_consent_record(
            session=session,
            user_id=current_user_id,
            fallback_to_global=fallback_to_global,
        )

        if record is None:
            filter_msg = (
                f"for current user (id={current_user_id})"
                if current_user_id is not None
                else "without user_id"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No consent record found {filter_msg}",
            )

        return _consent_record_to_summary(record)


@router.get("/{consent_id}", response_model=ConsentRecordSummary)
def get_consent_record(
    consent_id: Annotated[int, Path(description="Consent record ID")],
    current_user_id: Annotated[int | None, Depends(get_current_user)],
) -> ConsentRecordSummary:
    """Get a specific consent record by ID.

    Only allows access to records owned by the current user or global records.

    Args:
        consent_id: The ID of the consent record to retrieve.
        current_user_id: Current authenticated user ID from dependency.

    Returns:
        ConsentRecordSummary: The consent record.

    Raises:
        HTTPException: If the consent record is not found (404) or access is forbidden (403).
    """
    with get_session() as session:
        record = session.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consent record with id {consent_id} not found",
            )

        # Verify ownership
        _verify_record_ownership(record, current_user_id)

        return _consent_record_to_summary(record)


@router.patch("/{consent_id}", response_model=ConsentRecordSummary)
def update_consent_record(
    consent_id: Annotated[int, Path(description="Consent record ID")],
    update_request: ConsentUpdateRequest,
    current_user_id: Annotated[int | None, Depends(get_current_user)],
) -> ConsentRecordSummary:
    """Update an existing consent record.

    Only allows updating records owned by the current user.
    Global records (user_id is None) can be updated by anyone.

    Note: This updates the existing record rather than creating a new one.
    For tracking consent history, consider creating a new record instead.

    Args:
        consent_id: The ID of the consent record to update.
        update_request: Fields to update.
        current_user_id: Current authenticated user ID from dependency.

    Returns:
        ConsentRecordSummary: The updated consent record.

    Raises:
        HTTPException: If the consent record is not found (404) or access is forbidden (403).
    """
    with get_session() as session:
        record = session.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consent record with id {consent_id} not found",
            )

        # Verify ownership before allowing update
        _verify_record_ownership(record, current_user_id)

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
    current_user_id: Annotated[int | None, Depends(get_current_user)],
) -> None:
    """Delete a consent record.

    Only allows deleting records owned by the current user.
    Global records (user_id is None) can be deleted by anyone.

    Args:
        consent_id: The ID of the consent record to delete.
        current_user_id: Current authenticated user ID from dependency.

    Raises:
        HTTPException: If the consent record is not found (404) or access is forbidden (403).
    """
    with get_session() as session:
        record = session.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consent record with id {consent_id} not found",
            )

        # Verify ownership before allowing deletion
        _verify_record_ownership(record, current_user_id)

        session.delete(record)


@router.get("/llm/config", response_model=LLMConfigResponse)
def get_llm_config(
    current_user_id: Annotated[int | None, Depends(get_current_user)],
) -> LLMConfigResponse:
    """Check LLM configuration status based on the latest consent record for the current user.

    Args:
        current_user_id: Current authenticated user ID from dependency.

    Returns:
        LLMConfigResponse: LLM configuration status and preferences.
    """
    # Load the latest consent record for the user
    consent_tool = ConsentTool()

    with get_session() as session:
        record = _get_latest_consent_record(
            session=session,
            user_id=current_user_id,
            fallback_to_global=True,
        )

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

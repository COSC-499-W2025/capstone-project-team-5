"""Work experience service for managing user work history.

This service provides CRUD operations for WorkExperience data,
used by the TUI and REST API endpoints for resume generation.

TODO:
    - Add upsert_work_experience() for consistency with user_profile service
    - Add reorder_work_experiences() for bulk rank updates
    - Extract _get_user_by_username to shared utils (duplicated in user_profile.py)
    - Add custom exceptions instead of returning None for better error handling
    - Add JSON serialization helpers for bullets field
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TypedDict

from sqlalchemy.orm import Session

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User, WorkExperience

logger = logging.getLogger(__name__)

__all__ = [
    "WorkExperienceData",
    "get_work_experiences",
    "get_work_experience",
    "create_work_experience",
    "update_work_experience",
    "delete_work_experience",
]

# Fields that can be updated on WorkExperience
_WORK_EXP_FIELDS = (
    "company",
    "title",
    "location",
    "start_date",
    "end_date",
    "description",
    "bullets",
    "is_current",
    "rank",
)


class WorkExperienceData(TypedDict, total=False):
    """TypedDict for work experience data."""

    company: str
    title: str
    location: str
    start_date: date
    end_date: date
    description: str
    bullets: str  # JSON array as string
    is_current: bool
    rank: int


def _work_exp_to_dict(work_exp: WorkExperience) -> dict:
    """Convert a WorkExperience model to a dictionary.

    Args:
        work_exp: WorkExperience model instance

    Returns:
        Dictionary with work experience data
    """
    return {
        "id": work_exp.id,
        "user_id": work_exp.user_id,
        "company": work_exp.company,
        "title": work_exp.title,
        "location": work_exp.location,
        "start_date": work_exp.start_date,
        "end_date": work_exp.end_date,
        "description": work_exp.description,
        "bullets": work_exp.bullets,
        "is_current": work_exp.is_current,
        "rank": work_exp.rank,
        "updated_at": work_exp.updated_at,
    }


def _get_user_by_username(session: Session, username: str) -> User | None:
    """Get a user by username."""
    return session.query(User).filter(User.username == username).first()


def _get_work_exp_by_id(session: Session, user_id: int, work_exp_id: int) -> WorkExperience | None:
    """Get a work experience by ID, ensuring it belongs to the user."""
    return (
        session.query(WorkExperience)
        .filter(WorkExperience.id == work_exp_id, WorkExperience.user_id == user_id)
        .first()
    )


def _validate_work_exp_data(work_exp_data: WorkExperienceData) -> str | None:
    """Validate work experience data.

    Args:
        work_exp_data: Dictionary containing work experience fields

    Returns:
        Error message if validation fails, None if valid
    """
    start_date = work_exp_data.get("start_date")
    end_date = work_exp_data.get("end_date")
    is_current = work_exp_data.get("is_current", False)

    # Validate end_date is not before start_date
    if start_date and end_date and end_date < start_date:
        return "end_date cannot be before start_date"

    # Validate is_current and end_date are mutually exclusive
    if is_current and end_date:
        return "end_date must be None when is_current is True"

    return None


def _apply_work_exp_updates(work_exp: WorkExperience, work_exp_data: WorkExperienceData) -> None:
    """Apply updates from work_exp_data to a WorkExperience model."""
    for field in _WORK_EXP_FIELDS:
        if field in work_exp_data:
            setattr(work_exp, field, work_exp_data[field])

    # Auto-clear end_date if is_current is set to True
    if work_exp_data.get("is_current") is True:
        work_exp.end_date = None


def get_work_experiences(username: str) -> list[dict] | None:
    """Get all work experiences for a user, ordered by rank.

    Args:
        username: Username of the user

    Returns:
        List of work experience dictionaries, or None if user not found
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            work_exps = (
                session.query(WorkExperience)
                .filter(WorkExperience.user_id == user.id)
                .order_by(WorkExperience.rank, WorkExperience.id)
                .all()
            )

            return [_work_exp_to_dict(w) for w in work_exps]

    except Exception:
        logger.exception("Failed to get work experiences for %s", username)
        return None


def get_work_experience(username: str, work_exp_id: int) -> dict | None:
    """Get a specific work experience by ID.

    Args:
        username: Username of the user
        work_exp_id: ID of the work experience

    Returns:
        Dictionary with work experience data, or None if not found
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            work_exp = _get_work_exp_by_id(session, user.id, work_exp_id)
            if not work_exp:
                return None

            return _work_exp_to_dict(work_exp)

    except Exception:
        logger.exception("Failed to get work experience %d for %s", work_exp_id, username)
        return None


def create_work_experience(username: str, work_exp_data: WorkExperienceData) -> dict | None:
    """Create a new work experience entry.

    Args:
        username: Username of the user
        work_exp_data: Dictionary containing work experience fields.
                       Must include 'company' and 'title'.

    Returns:
        Dictionary with created work experience data, or None if creation failed
    """
    if "company" not in work_exp_data or "title" not in work_exp_data:
        return None

    validation_error = _validate_work_exp_data(work_exp_data)
    if validation_error:
        logger.warning("Validation failed for work experience: %s", validation_error)
        return None

    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            new_work_exp = WorkExperience(
                user_id=user.id,
                company=work_exp_data["company"],
                title=work_exp_data["title"],
            )
            _apply_work_exp_updates(new_work_exp, work_exp_data)

            session.add(new_work_exp)
            session.commit()

            return _work_exp_to_dict(new_work_exp)

    except Exception:
        logger.exception("Failed to create work experience for %s", username)
        return None


def update_work_experience(
    username: str, work_exp_id: int, work_exp_data: WorkExperienceData
) -> dict | None:
    """Update an existing work experience entry.

    Args:
        username: Username of the user
        work_exp_id: ID of the work experience to update
        work_exp_data: Dictionary containing fields to update

    Returns:
        Dictionary with updated work experience data, or None if update failed
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            work_exp = _get_work_exp_by_id(session, user.id, work_exp_id)
            if not work_exp:
                return None

            # Merge existing values with updates for validation
            # If is_current is being set to True, treat end_date as None for validation
            new_is_current = work_exp_data.get("is_current", work_exp.is_current)
            effective_end_date = (
                None if new_is_current else work_exp_data.get("end_date", work_exp.end_date)
            )
            merged_data: WorkExperienceData = {
                "start_date": work_exp_data.get("start_date", work_exp.start_date),
                "end_date": effective_end_date,
                "is_current": new_is_current,
            }
            validation_error = _validate_work_exp_data(merged_data)
            if validation_error:
                logger.warning("Validation failed for work experience update: %s", validation_error)
                return None

            _apply_work_exp_updates(work_exp, work_exp_data)
            session.commit()

            return _work_exp_to_dict(work_exp)

    except Exception:
        logger.exception("Failed to update work experience %d for %s", work_exp_id, username)
        return None


def delete_work_experience(username: str, work_exp_id: int) -> bool:
    """Delete a work experience entry.

    Args:
        username: Username of the user
        work_exp_id: ID of the work experience to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return False

            work_exp = _get_work_exp_by_id(session, user.id, work_exp_id)
            if not work_exp:
                return False

            session.delete(work_exp)
            session.commit()
            return True

    except Exception:
        logger.exception("Failed to delete work experience %d for %s", work_exp_id, username)
        return False

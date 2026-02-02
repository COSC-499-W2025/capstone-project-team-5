"""Education service for managing user educational history.

This service provides CRUD operations for Education data.

TODO:
    - Add upsert_education() for consistency with user_profile service
    - Add reorder_educations() for bulk rank updates
    - Extract _get_user_by_username to shared utils (duplicated in user_profile.py)
    - Add custom exceptions instead of returning None for better error handling
    - Add JSON serialization helpers for achievements field
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TypedDict

from sqlalchemy.orm import Session

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Education, User

logger = logging.getLogger(__name__)

__all__ = [
    "EducationData",
    "get_educations",
    "get_education",
    "create_education",
    "update_education",
    "delete_education",
]

# Fields that can be updated on Education
_EDUCATION_FIELDS = (
    "institution",
    "degree",
    "field_of_study",
    "gpa",
    "start_date",
    "end_date",
    "achievements",
    "is_current",
    "rank",
)


class EducationData(TypedDict, total=False):
    """TypedDict for education data."""

    institution: str
    degree: str
    field_of_study: str
    gpa: float
    start_date: date
    end_date: date
    achievements: str  # JSON array as string
    is_current: bool
    rank: int


def _education_to_dict(education: Education) -> dict:
    """Convert an Education model to a dictionary.

    Args:
        education: Education model instance

    Returns:
        Dictionary with education data
    """
    return {
        "id": education.id,
        "user_id": education.user_id,
        "institution": education.institution,
        "degree": education.degree,
        "field_of_study": education.field_of_study,
        "gpa": education.gpa,
        "start_date": education.start_date,
        "end_date": education.end_date,
        "achievements": education.achievements,
        "is_current": education.is_current,
        "rank": education.rank,
        "updated_at": education.updated_at,
    }


def _get_user_by_username(session: Session, username: str) -> User | None:
    """Get a user by username."""
    return session.query(User).filter(User.username == username).first()


def _get_education_by_id(session: Session, user_id: int, education_id: int) -> Education | None:
    """Get an education entry by ID, ensuring it belongs to the user."""
    return (
        session.query(Education)
        .filter(Education.id == education_id, Education.user_id == user_id)
        .first()
    )


def _validate_education_data(education_data: EducationData) -> str | None:
    """Validate education data.

    Args:
        education_data: Dictionary containing education fields

    Returns:
        Error message if validation fails, None if valid
    """
    start_date = education_data.get("start_date")
    end_date = education_data.get("end_date")
    is_current = education_data.get("is_current", False)
    gpa = education_data.get("gpa")

    # Validate end_date is not before start_date
    if start_date and end_date and end_date < start_date:
        return "end_date cannot be before start_date"

    # Validate is_current and end_date are mutually exclusive
    if is_current and end_date:
        return "end_date must be None when is_current is True"

    # Validate GPA is in valid range (0.0 to 4.0 for US, allowing up to 5.0 for weighted)
    if gpa is not None and (gpa < 0.0 or gpa > 5.0):
        return "gpa must be between 0.0 and 5.0"

    return None


def _apply_education_updates(education: Education, education_data: EducationData) -> None:
    """Apply updates from education_data to an Education model."""
    for field in _EDUCATION_FIELDS:
        if field in education_data:
            setattr(education, field, education_data[field])

    # Auto-clear end_date if is_current is set to True
    if education_data.get("is_current") is True:
        education.end_date = None


def get_educations(username: str) -> list[dict] | None:
    """Get all education entries for a user, ordered by rank.

    Args:
        username: Username of the user

    Returns:
        List of education dictionaries, or None if user not found
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            educations = (
                session.query(Education)
                .filter(Education.user_id == user.id)
                .order_by(Education.rank, Education.id)
                .all()
            )

            return [_education_to_dict(e) for e in educations]

    except Exception:
        logger.exception("Failed to get educations for %s", username)
        return None


def get_education(username: str, education_id: int) -> dict | None:
    """Get a specific education entry by ID.

    Args:
        username: Username of the user
        education_id: ID of the education entry

    Returns:
        Dictionary with education data, or None if not found
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            education = _get_education_by_id(session, user.id, education_id)
            if not education:
                return None

            return _education_to_dict(education)

    except Exception:
        logger.exception("Failed to get education %d for %s", education_id, username)
        return None


def create_education(username: str, education_data: EducationData) -> dict | None:
    """Create a new education entry.

    Args:
        username: Username of the user
        education_data: Dictionary containing education fields.
                       Must include 'institution' and 'degree'.

    Returns:
        Dictionary with created education data, or None if creation failed
    """
    if "institution" not in education_data or "degree" not in education_data:
        return None

    validation_error = _validate_education_data(education_data)
    if validation_error:
        logger.warning("Validation failed for education: %s", validation_error)
        return None

    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            new_education = Education(
                user_id=user.id,
                institution=education_data["institution"],
                degree=education_data["degree"],
            )
            _apply_education_updates(new_education, education_data)

            session.add(new_education)
            session.commit()

            return _education_to_dict(new_education)

    except Exception:
        logger.exception("Failed to create education for %s", username)
        return None


def update_education(
    username: str, education_id: int, education_data: EducationData
) -> dict | None:
    """Update an existing education entry.

    Args:
        username: Username of the user
        education_id: ID of the education entry to update
        education_data: Dictionary containing fields to update

    Returns:
        Dictionary with updated education data, or None if update failed
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            education = _get_education_by_id(session, user.id, education_id)
            if not education:
                return None

            # Merge existing values with updates for validation
            # If is_current is being set to True, treat end_date as None for validation
            new_is_current = education_data.get("is_current", education.is_current)
            effective_end_date = (
                None if new_is_current else education_data.get("end_date", education.end_date)
            )
            merged_data: EducationData = {
                "start_date": education_data.get("start_date", education.start_date),
                "end_date": effective_end_date,
                "is_current": new_is_current,
                "gpa": education_data.get("gpa", education.gpa),
            }
            validation_error = _validate_education_data(merged_data)
            if validation_error:
                logger.warning("Validation failed for education update: %s", validation_error)
                return None

            _apply_education_updates(education, education_data)
            session.commit()

            return _education_to_dict(education)

    except Exception:
        logger.exception("Failed to update education %d for %s", education_id, username)
        return None


def delete_education(username: str, education_id: int) -> bool:
    """Delete an education entry.

    Args:
        username: Username of the user
        education_id: ID of the education entry to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return False

            education = _get_education_by_id(session, user.id, education_id)
            if not education:
                return False

            session.delete(education)
            session.commit()
            return True

    except Exception:
        logger.exception("Failed to delete education %d for %s", education_id, username)
        return False

"""User profile service for managing user contact and personal information.

This service provides CRUD operations for UserProfile data,
used by the TUI and REST API endpoints for resume generation.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from sqlalchemy.orm import Session

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User, UserProfile

logger = logging.getLogger(__name__)

__all__ = [
    "UserProfileData",
    "get_user_profile",
    "create_user_profile",
    "update_user_profile",
    "upsert_user_profile",
    "delete_user_profile",
]

# Fields that can be updated on UserProfile
_PROFILE_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "phone",
    "address",
    "city",
    "state",
    "zip_code",
    "linkedin_url",
    "github_username",
    "website",
)


class UserProfileData(TypedDict, total=False):
    """TypedDict for user profile data."""

    first_name: str
    last_name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    zip_code: str
    linkedin_url: str
    github_username: str
    website: str


def _profile_to_dict(profile: UserProfile) -> dict:
    """Convert a UserProfile model to a dictionary.

    Args:
        profile: UserProfile model instance

    Returns:
        Dictionary with profile data
    """
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "phone": profile.phone,
        "address": profile.address,
        "city": profile.city,
        "state": profile.state,
        "zip_code": profile.zip_code,
        "linkedin_url": profile.linkedin_url,
        "github_username": profile.github_username,
        "website": profile.website,
        "updated_at": profile.updated_at,
    }


def _get_user_by_username(session: Session, username: str) -> User | None:
    """Get a user by username.

    Args:
        session: SQLAlchemy session
        username: Username to look up

    Returns:
        User model or None if not found
    """
    return session.query(User).filter(User.username == username).first()


def _get_profile_by_user_id(session: Session, user_id: int) -> UserProfile | None:
    """Get a user profile by user ID.

    Args:
        session: SQLAlchemy session
        user_id: User ID to look up

    Returns:
        UserProfile model or None if not found
    """
    return session.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def _apply_profile_updates(profile: UserProfile, profile_data: UserProfileData) -> None:
    """Apply updates from profile_data to a UserProfile model.

    Args:
        profile: UserProfile model to update
        profile_data: Dictionary containing fields to update
    """
    for field in _PROFILE_FIELDS:
        if field in profile_data:
            setattr(profile, field, profile_data[field])


def get_user_profile(username: str) -> dict | None:
    """Get a user's profile information.

    Args:
        username: Username of the user

    Returns:
        Dictionary with profile data, or None if user or profile not found
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            profile = _get_profile_by_user_id(session, user.id)
            if not profile:
                return None

            return _profile_to_dict(profile)

    except Exception:
        logger.exception("Failed to get user profile for %s", username)
        return None


def create_user_profile(username: str, profile_data: UserProfileData) -> dict | None:
    """Create a new user profile.

    Args:
        username: Username of the user
        profile_data: Dictionary containing profile fields

    Returns:
        Dictionary with created profile data, or None if creation failed
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            # Check if profile already exists
            existing = _get_profile_by_user_id(session, user.id)
            if existing:
                return None  # Profile already exists, use update instead

            new_profile = UserProfile(user_id=user.id)
            _apply_profile_updates(new_profile, profile_data)

            session.add(new_profile)
            session.commit()

            return _profile_to_dict(new_profile)

    except Exception:
        logger.exception("Failed to create user profile for %s", username)
        return None


def update_user_profile(username: str, profile_data: UserProfileData) -> dict | None:
    """Update an existing user profile.

    Args:
        username: Username of the user
        profile_data: Dictionary containing profile fields to update

    Returns:
        Dictionary with updated profile data, or None if update failed
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            profile = _get_profile_by_user_id(session, user.id)
            if not profile:
                return None  # Profile doesn't exist, use create instead

            _apply_profile_updates(profile, profile_data)
            session.commit()

            return _profile_to_dict(profile)

    except Exception:
        logger.exception("Failed to update user profile for %s", username)
        return None


def upsert_user_profile(username: str, profile_data: UserProfileData) -> dict | None:
    """Create or update a user profile in a single transaction.

    This is a convenience function that creates a profile if it doesn't exist,
    or updates it if it does.

    Args:
        username: Username of the user
        profile_data: Dictionary containing profile fields

    Returns:
        Dictionary with profile data, or None if operation failed
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return None

            profile = _get_profile_by_user_id(session, user.id)

            if profile:
                # Update existing profile
                _apply_profile_updates(profile, profile_data)
            else:
                # Create new profile
                profile = UserProfile(user_id=user.id)
                _apply_profile_updates(profile, profile_data)
                session.add(profile)

            session.commit()
            return _profile_to_dict(profile)

    except Exception:
        logger.exception("Failed to upsert user profile for %s", username)
        return None


def delete_user_profile(username: str) -> bool:
    """Delete a user's profile.

    Args:
        username: Username of the user

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        with get_session() as session:
            user = _get_user_by_username(session, username)
            if not user:
                return False

            profile = _get_profile_by_user_id(session, user.id)
            if not profile:
                return False

            session.delete(profile)
            session.commit()
            return True

    except Exception:
        logger.exception("Failed to delete user profile for %s", username)
        return False

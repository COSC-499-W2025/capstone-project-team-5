"""User and user profile routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from capstone_project_team_5.api.schemas.users import (
    UserInfoResponse,
    UserProfileCreateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User
from capstone_project_team_5.services.user_profile import (
    create_user_profile,
    get_user_profile,
    upsert_user_profile,
)

router = APIRouter(prefix="/users", tags=["users"])


def get_current_username(
    x_username: Annotated[
        str | None,
        Header(
            description=(
                "Current username. In production, this should be extracted "
                "from authenticated session/JWT token."
            )
        ),
    ] = None,
) -> str:
    """Get the current username from request context.

    NOTE: This is a simplified implementation using a header.
    In production, this should:
    - Extract username from authenticated session/JWT token
    - Validate the session is active and valid
    - Raise 401 if authentication is missing or invalid

    Args:
        x_username: Username from X-Username header (temporary mechanism).

    Returns:
        str: Authenticated username.

    Raises:
        HTTPException: If authentication is missing (401).
    """
    if not x_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Please provide X-Username header.",
        )
    return x_username


@router.get("/me", response_model=UserInfoResponse)
def get_current_user_info(
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserInfoResponse:
    """Get the current authenticated user's basic information.

    Args:
        current_username: Current username from authentication.

    Returns:
        UserInfoResponse: Basic user information.

    Raises:
        HTTPException: If user not found (404).
    """
    with get_session() as session:
        user = session.query(User).filter(User.username == current_username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{current_username}' not found",
            )
        return UserInfoResponse.model_validate(user)


@router.get("/{username}/profile", response_model=UserProfileResponse)
def get_profile(
    username: Annotated[str, Path(description="Username whose profile to retrieve")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserProfileResponse:
    """Get user profile by username.

    Users can only access their own profile data.

    Args:
        username: Username whose profile to retrieve.
        current_username: Current username from authentication.

    Returns:
        UserProfileResponse: User profile data.

    Raises:
        HTTPException: If user not found (404), profile not found (404),
            or access denied (403).
    """
    # Verify user has permission to access this profile
    if current_username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this profile",
        )

    # Verify user exists
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

    # Get profile
    profile_dict = get_user_profile(username)
    if not profile_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for user '{username}'",
        )

    return UserProfileResponse(**profile_dict)


@router.post(
    "/{username}/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    username: Annotated[str, Path(description="Username to create profile for")],
    profile_data: UserProfileCreateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserProfileResponse:
    """Create a new user profile.

    Users can only create their own profile.

    Args:
        username: Username to create profile for.
        profile_data: Profile data to create.
        current_username: Current username from authentication.

    Returns:
        UserProfileResponse: Created profile data.

    Raises:
        HTTPException: If user not found (404), profile already exists (409),
            or access denied (403).
    """
    # Verify user has permission to create this profile
    if current_username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create your own profile",
        )

    # Verify user exists
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

    # Check if profile already exists
    existing_profile = get_user_profile(username)
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile already exists for user '{username}'. Use PATCH to update.",
        )

    # Create profile
    profile_dict = profile_data.model_dump()
    result = create_user_profile(username, profile_dict)

    return UserProfileResponse(**result)


@router.patch("/{username}/profile", response_model=UserProfileResponse)
def upsert_profile(
    username: Annotated[str, Path(description="Username to create/update profile for")],
    profile_data: UserProfileUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserProfileResponse:
    """Create or update user profile (upsert).

    This endpoint will create a new profile if one doesn't exist,
    or update the existing profile with the provided fields.
    Only the fields provided in the request will be updated.

    Users can only modify their own profile.

    Args:
        username: Username to create/update profile for.
        profile_data: Profile data to create/update.
        current_username: Current username from authentication.

    Returns:
        UserProfileResponse: Created or updated profile data.

    Raises:
        HTTPException: If user not found (404) or access denied (403).
    """
    # Verify user has permission to modify this profile
    if current_username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own profile",
        )

    # Verify user exists
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

    # Upsert profile
    profile_dict = profile_data.model_dump(exclude_unset=True)
    result = upsert_user_profile(username, profile_dict)

    return UserProfileResponse(**result)

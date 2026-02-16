"""User and user profile routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from capstone_project_team_5.api.schemas.users import (
    UserInfoResponse,
    UserProfileCreateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserWithProfileResponse,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User
from capstone_project_team_5.services.user_profile import (
    create_user_profile,
    delete_user_profile,
    get_user_profile,
    update_user_profile,
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
        str: The current username.

    Raises:
        HTTPException: If no username is provided (401 Unauthorized).
    """
    if not x_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide X-Username header.",
        )
    return x_username


def _verify_user_access(current_username: str, requested_username: str) -> None:
    """Verify that the current user can access the requested user's data.

    Args:
        current_username: The authenticated user's username.
        requested_username: The username being accessed.

    Raises:
        HTTPException: If user doesn't have permission (403 Forbidden).
    """
    if current_username != requested_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this user's data",
        )


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


@router.get("/{username}", response_model=UserInfoResponse)
def get_user_info(
    username: Annotated[str, Path(description="Username to retrieve")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserInfoResponse:
    """Get basic user information by username.

    Args:
        username: Username to retrieve.
        current_username: Current username from authentication.

    Returns:
        UserInfoResponse: Basic user information.

    Raises:
        HTTPException: If user not found (404) or access denied (403).
    """
    _verify_user_access(current_username, username)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )
        return UserInfoResponse.model_validate(user)


@router.get("/{username}/full", response_model=UserWithProfileResponse)
def get_user_with_profile(
    username: Annotated[str, Path(description="Username to retrieve")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserWithProfileResponse:
    """Get user information with profile data.

    Args:
        username: Username to retrieve.
        current_username: Current username from authentication.

    Returns:
        UserWithProfileResponse: User info and profile data.

    Raises:
        HTTPException: If user not found (404) or access denied (403).
    """
    _verify_user_access(current_username, username)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

        # Get profile if it exists
        profile_dict = get_user_profile(username)
        profile = UserProfileResponse(**profile_dict) if profile_dict else None

        return UserWithProfileResponse(
            user=UserInfoResponse.model_validate(user),
            profile=profile,
        )


@router.get("/{username}/profile", response_model=UserProfileResponse)
def get_profile(
    username: Annotated[str, Path(description="Username whose profile to retrieve")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserProfileResponse:
    """Get a user's profile information.

    Args:
        username: Username whose profile to retrieve.
        current_username: Current username from authentication.

    Returns:
        UserProfileResponse: User profile data.

    Raises:
        HTTPException: If user not found (404), profile not found (404),
            or access denied (403).
    """
    _verify_user_access(current_username, username)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

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
    """Create a new profile for a user.

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
    _verify_user_access(current_username, username)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

    # Convert request to dict, excluding None values if desired
    profile_dict = profile_data.model_dump(exclude_none=True)

    result = create_user_profile(username, profile_dict)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile already exists for user '{username}'. Use PUT to update.",
        )

    return UserProfileResponse(**result)


@router.put("/{username}/profile", response_model=UserProfileResponse)
def update_profile(
    username: Annotated[str, Path(description="Username whose profile to update")],
    profile_data: UserProfileUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserProfileResponse:
    """Update an existing user profile.

    Args:
        username: Username whose profile to update.
        profile_data: Profile data to update.
        current_username: Current username from authentication.

    Returns:
        UserProfileResponse: Updated profile data.

    Raises:
        HTTPException: If user not found (404), profile not found (404),
            or access denied (403).
    """
    _verify_user_access(current_username, username)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

    # Convert request to dict, including None values to allow clearing fields
    profile_dict = profile_data.model_dump()

    result = update_user_profile(username, profile_dict)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for user '{username}'. Use POST to create.",
        )

    return UserProfileResponse(**result)


@router.patch("/{username}/profile", response_model=UserProfileResponse)
def upsert_profile(
    username: Annotated[str, Path(description="Username to create/update profile for")],
    profile_data: UserProfileUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> UserProfileResponse:
    """Create or update a user profile (upsert operation).

    This endpoint will create the profile if it doesn't exist,
    or update it if it does.

    Args:
        username: Username to create/update profile for.
        profile_data: Profile data.
        current_username: Current username from authentication.

    Returns:
        UserProfileResponse: Created or updated profile data.

    Raises:
        HTTPException: If user not found (404) or access denied (403).
    """
    _verify_user_access(current_username, username)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

    # Convert request to dict, excluding None values for upsert
    profile_dict = profile_data.model_dump(exclude_none=True)

    result = upsert_user_profile(username, profile_dict)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or update profile",
        )

    return UserProfileResponse(**result)


@router.delete("/{username}/profile", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    username: Annotated[str, Path(description="Username whose profile to delete")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> None:
    """Delete a user's profile.

    Args:
        username: Username whose profile to delete.
        current_username: Current username from authentication.

    Raises:
        HTTPException: If user not found (404), profile not found (404),
            or access denied (403).
    """
    _verify_user_access(current_username, username)

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )

    success = delete_user_profile(username)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found for user '{username}'",
        )

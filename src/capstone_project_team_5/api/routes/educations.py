"""Education routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from capstone_project_team_5.api.dependencies import get_current_username
from capstone_project_team_5.api.schemas.educations import (
    EducationCreateRequest,
    EducationResponse,
    EducationUpdateRequest,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User
from capstone_project_team_5.services.education import (
    create_education,
    delete_education,
    get_education,
    get_educations,
    update_education,
)

router = APIRouter(prefix="/users", tags=["educations"])


def _verify_permission_and_user(current_username: str, username: str) -> None:
    """Verify the current user has permission and the target user exists.

    Raises:
        HTTPException: 403 if no permission, 404 if user not found.
    """
    if current_username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own education entries",
        )
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )


@router.get(
    "/{username}/educations",
    response_model=list[EducationResponse],
)
def list_educations(
    username: Annotated[str, Path(description="Username")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> list[EducationResponse]:
    """List all education entries for a user, ordered by rank."""
    _verify_permission_and_user(current_username, username)

    results = get_educations(username)
    if results is None:
        return []

    return [EducationResponse(**r) for r in results]


@router.get(
    "/{username}/educations/{education_id}",
    response_model=EducationResponse,
)
def get_education_by_id(
    username: Annotated[str, Path(description="Username")],
    education_id: Annotated[int, Path(description="Education entry ID")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> EducationResponse:
    """Get a specific education entry by ID."""
    _verify_permission_and_user(current_username, username)

    result = get_education(username, education_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Education entry {education_id} not found",
        )

    return EducationResponse(**result)


@router.post(
    "/{username}/educations",
    response_model=EducationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_education_endpoint(
    username: Annotated[str, Path(description="Username")],
    data: EducationCreateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> EducationResponse:
    """Create a new education entry."""
    _verify_permission_and_user(current_username, username)

    edu_dict = data.model_dump()
    result = create_education(username, edu_dict)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create education entry. Check that dates are valid, "
            "end_date is not set when is_current is True, "
            "and GPA is between 0.0 and 5.0.",
        )

    return EducationResponse(**result)


@router.patch(
    "/{username}/educations/{education_id}",
    response_model=EducationResponse,
)
def update_education_endpoint(
    username: Annotated[str, Path(description="Username")],
    education_id: Annotated[int, Path(description="Education entry ID")],
    data: EducationUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> EducationResponse:
    """Update an existing education entry. Only provided fields are updated."""
    _verify_permission_and_user(current_username, username)

    update_dict = data.model_dump(exclude_unset=True)
    result = update_education(username, education_id, update_dict)
    if not result:
        existing = get_education(username, education_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Education entry {education_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update education entry. Check that dates are valid, "
            "end_date is not set when is_current is True, "
            "and GPA is between 0.0 and 5.0.",
        )

    return EducationResponse(**result)


@router.delete(
    "/{username}/educations/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_education_endpoint(
    username: Annotated[str, Path(description="Username")],
    education_id: Annotated[int, Path(description="Education entry ID")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> None:
    """Delete an education entry."""
    _verify_permission_and_user(current_username, username)

    success = delete_education(username, education_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Education entry {education_id} not found",
        )

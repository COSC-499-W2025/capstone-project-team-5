"""Work experience routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from capstone_project_team_5.api.dependencies import get_current_username
from capstone_project_team_5.api.schemas.work_experiences import (
    WorkExperienceCreateRequest,
    WorkExperienceResponse,
    WorkExperienceUpdateRequest,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User
from capstone_project_team_5.services.work_experience import (
    create_work_experience,
    delete_work_experience,
    get_work_experience,
    get_work_experiences,
    update_work_experience,
)

router = APIRouter(prefix="/users", tags=["work-experiences"])


def _verify_permission_and_user(current_username: str, username: str) -> None:
    """Verify the current user has permission and the target user exists.

    Raises:
        HTTPException: 403 if no permission, 404 if user not found.
    """
    if current_username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own work experiences",
        )
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )


@router.get(
    "/{username}/work-experiences",
    response_model=list[WorkExperienceResponse],
)
def list_work_experiences(
    username: Annotated[str, Path(description="Username")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> list[WorkExperienceResponse]:
    """List all work experiences for a user, ordered by rank."""
    _verify_permission_and_user(current_username, username)

    results = get_work_experiences(username)
    if results is None:
        return []

    return [WorkExperienceResponse(**r) for r in results]


@router.get(
    "/{username}/work-experiences/{work_exp_id}",
    response_model=WorkExperienceResponse,
)
def get_work_experience_by_id(
    username: Annotated[str, Path(description="Username")],
    work_exp_id: Annotated[int, Path(description="Work experience ID")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> WorkExperienceResponse:
    """Get a specific work experience by ID."""
    _verify_permission_and_user(current_username, username)

    result = get_work_experience(username, work_exp_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work experience {work_exp_id} not found",
        )

    return WorkExperienceResponse(**result)


@router.post(
    "/{username}/work-experiences",
    response_model=WorkExperienceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_work_experience_endpoint(
    username: Annotated[str, Path(description="Username")],
    data: WorkExperienceCreateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> WorkExperienceResponse:
    """Create a new work experience entry."""
    _verify_permission_and_user(current_username, username)

    work_exp_dict = data.model_dump()
    result = create_work_experience(username, work_exp_dict)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create work experience. Check that dates are valid "
            "and end_date is not set when is_current is True.",
        )

    return WorkExperienceResponse(**result)


@router.patch(
    "/{username}/work-experiences/{work_exp_id}",
    response_model=WorkExperienceResponse,
)
def update_work_experience_endpoint(
    username: Annotated[str, Path(description="Username")],
    work_exp_id: Annotated[int, Path(description="Work experience ID")],
    data: WorkExperienceUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> WorkExperienceResponse:
    """Update an existing work experience entry. Only provided fields are updated."""
    _verify_permission_and_user(current_username, username)

    update_dict = data.model_dump(exclude_unset=True)
    result = update_work_experience(username, work_exp_id, update_dict)
    if not result:
        existing = get_work_experience(username, work_exp_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Work experience {work_exp_id} not found",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update work experience. Check that dates are valid "
            "and end_date is not set when is_current is True.",
        )

    return WorkExperienceResponse(**result)


@router.delete(
    "/{username}/work-experiences/{work_exp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_work_experience_endpoint(
    username: Annotated[str, Path(description="Username")],
    work_exp_id: Annotated[int, Path(description="Work experience ID")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> None:
    """Delete a work experience entry."""
    _verify_permission_and_user(current_username, username)

    success = delete_work_experience(username, work_exp_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work experience {work_exp_id} not found",
        )

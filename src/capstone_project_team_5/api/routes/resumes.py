"""Resume routes for the API."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi import Path as PathParam
from fastapi.responses import FileResponse

from capstone_project_team_5.api.dependencies import get_current_username
from capstone_project_team_5.api.schemas.resumes import (
    ResumeGenerateRequest,
    ResumeProjectCreateRequest,
    ResumeProjectResponse,
    ResumeProjectUpdateRequest,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User
from capstone_project_team_5.services.resume import (
    delete_resume,
    get_all_resumes,
    get_resume,
    save_resume,
)
from capstone_project_team_5.services.resume_generator import generate_resume_pdf

router = APIRouter(prefix="/users", tags=["resumes"])


def _verify_permission_and_user(current_username: str, username: str) -> None:
    """Verify the current user has permission and the target user exists.

    Raises:
        HTTPException: 403 if no permission, 404 if user not found.
    """
    if current_username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own resumes",
        )
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found",
            )


# --- /generate MUST come before /{project_id} to avoid path conflicts ---


@router.post(
    "/{username}/resumes/generate",
    responses={200: {"content": {"application/pdf": {}}}},
)
def generate_resume_endpoint(
    username: Annotated[str, PathParam(description="Username")],
    data: ResumeGenerateRequest,
    background_tasks: BackgroundTasks,
    current_username: Annotated[str, Depends(get_current_username)],
) -> FileResponse:
    """Generate and download a PDF resume."""
    _verify_permission_and_user(current_username, username)

    tmp_dir = tempfile.mkdtemp()
    try:
        output_stem = Path(tmp_dir) / f"{username}_resume"
        pdf_path = generate_resume_pdf(
            username,
            output_stem,
            template_name=data.template_name,
        )
    except FileNotFoundError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LaTeX compiler not found. Please install pdflatex.",
        ) from None
    except subprocess.CalledProcessError:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="LaTeX compilation failed. Check that all required packages are installed.",
        ) from None

    if pdf_path is None:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not generate resume. User profile may be missing.",
        )

    background_tasks.add_task(shutil.rmtree, tmp_dir, True)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{username}_resume.pdf",
    )


@router.get(
    "/{username}/resumes",
    response_model=list[ResumeProjectResponse],
)
def list_resumes(
    username: Annotated[str, PathParam(description="Username")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> list[ResumeProjectResponse]:
    """List all resume projects for a user, ordered by updated_at desc."""
    _verify_permission_and_user(current_username, username)

    results = get_all_resumes(username)
    return [ResumeProjectResponse(**r) for r in results]


@router.get(
    "/{username}/resumes/{project_id}",
    response_model=ResumeProjectResponse,
)
def get_resume_by_project(
    username: Annotated[str, PathParam(description="Username")],
    project_id: Annotated[int, PathParam(description="Project ID")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> ResumeProjectResponse:
    """Get a specific resume project by project ID."""
    _verify_permission_and_user(current_username, username)

    result = get_resume(username, project_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume for project {project_id} not found",
        )

    return ResumeProjectResponse(**result)


@router.post(
    "/{username}/resumes",
    response_model=ResumeProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resume_endpoint(
    username: Annotated[str, PathParam(description="Username")],
    data: ResumeProjectCreateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> ResumeProjectResponse:
    """Create or upsert a resume project entry."""
    _verify_permission_and_user(current_username, username)

    success = save_resume(
        username=username,
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        bullet_points=data.bullet_points,
        analysis_snapshot=data.analysis_snapshot,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save resume. Check that the project_id is valid.",
        )

    result = get_resume(username, data.project_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume was saved but could not be retrieved.",
        )

    return ResumeProjectResponse(**result)


@router.patch(
    "/{username}/resumes/{project_id}",
    response_model=ResumeProjectResponse,
)
def update_resume_endpoint(
    username: Annotated[str, PathParam(description="Username")],
    project_id: Annotated[int, PathParam(description="Project ID")],
    data: ResumeProjectUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> ResumeProjectResponse:
    """Partial update of a resume project. Merges with existing data."""
    _verify_permission_and_user(current_username, username)

    existing = get_resume(username, project_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume for project {project_id} not found",
        )

    update_fields = data.model_dump(exclude_unset=True)

    merged_title = update_fields.get("title", existing["title"] or "")
    merged_description = update_fields.get("description", existing["description"] or "")
    merged_bullets = update_fields.get("bullet_points", existing["bullet_points"])
    merged_snapshot = update_fields.get("analysis_snapshot", existing["analysis_snapshot"])

    success = save_resume(
        username=username,
        project_id=project_id,
        title=merged_title,
        description=merged_description,
        bullet_points=merged_bullets,
        analysis_snapshot=merged_snapshot,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update resume. Check that the project_id is valid.",
        )

    result = get_resume(username, project_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume was updated but could not be retrieved.",
        )

    return ResumeProjectResponse(**result)


@router.delete(
    "/{username}/resumes/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_resume_endpoint(
    username: Annotated[str, PathParam(description="Username")],
    project_id: Annotated[int, PathParam(description="Project ID")],
    current_username: Annotated[str, Depends(get_current_username)],
) -> None:
    """Delete a resume project entry."""
    _verify_permission_and_user(current_username, username)

    success = delete_resume(username, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume for project {project_id} not found",
        )

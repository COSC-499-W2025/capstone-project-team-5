"""Project routes for the API."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from sqlalchemy import desc

from capstone_project_team_5.api.schemas.projects import (
    ProjectSummary,
    ProjectUpdateRequest,
    ProjectUploadResponse,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, UploadRecord
from capstone_project_team_5.models.upload import InvalidZipError
from capstone_project_team_5.services.project_thumbnail import is_valid_thumbnail_url
from capstone_project_team_5.services.upload import upload_zip

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_to_summary(project: Project) -> ProjectSummary:
    return ProjectSummary(
        id=project.id,
        name=project.name,
        rel_path=project.rel_path,
        file_count=project.file_count,
        has_git_repo=project.has_git_repo,
        is_collaborative=project.is_collaborative,
        thumbnail_url=project.thumbnail_url,
        importance_rank=project.importance_rank,
        importance_score=project.importance_score,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _get_latest_upload_record(
    filename: str,
    size_bytes: int,
    file_count: int,
) -> UploadRecord | None:
    with get_session() as session:
        return (
            session.query(UploadRecord)
            .filter(
                UploadRecord.filename == filename,
                UploadRecord.size_bytes == size_bytes,
                UploadRecord.file_count == file_count,
            )
            .order_by(desc(UploadRecord.created_at))
            .first()
        )


@router.get(
    "/",
    response_model=list[ProjectSummary],
    summary="List projects",
    description="Return all persisted projects ordered by most recently updated.",
)
def list_projects() -> list[ProjectSummary]:
    with get_session() as session:
        projects = session.query(Project).order_by(desc(Project.updated_at)).all()
        return [_project_to_summary(project) for project in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectSummary,
    summary="Get a project",
    description="Return a single project by ID.",
    responses={404: {"description": "Project not found"}},
)
def get_project(project_id: int) -> ProjectSummary:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )
        return _project_to_summary(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectSummary,
    summary="Update a project",
    description="Update editable fields on a project by ID.",
    responses={404: {"description": "Project not found"}},
)
def update_project(project_id: int, update: ProjectUpdateRequest) -> ProjectSummary:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        updates = update.model_dump(exclude_unset=True)
        if "thumbnail_url" in updates:
            thumbnail_url = updates["thumbnail_url"]
            if thumbnail_url is not None and not is_valid_thumbnail_url(thumbnail_url):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid thumbnail URL.",
                )
        for field, value in updates.items():
            setattr(project, field, value)

        session.flush()
        session.refresh(project)
        return _project_to_summary(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Delete a project by ID.",
    responses={404: {"description": "Project not found"}},
)
def delete_project(project_id: int) -> Response:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )
        session.delete(project)
        return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/upload",
    response_model=ProjectUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a project archive",
    description="Upload a ZIP file and persist detected projects.",
    responses={
        400: {"description": "Invalid ZIP file"},
        500: {"description": "Upload could not be persisted"},
    },
)
async def upload_project_zip(
    file: Annotated[UploadFile, File(description="ZIP archive containing project files")],
) -> ProjectUploadResponse:
    filename = Path(file.filename or "upload.zip").name
    if not filename.lower().endswith(".zip"):
        filename = f"{filename}.zip"

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / filename
        temp_path.write_bytes(await file.read())

        try:
            result = upload_zip(temp_path)
        except InvalidZipError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        upload_record = _get_latest_upload_record(
            filename=result.filename,
            size_bytes=result.size_bytes,
            file_count=result.file_count,
        )
        if upload_record is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Upload record not found after processing.",
            )

        with get_session() as session:
            projects = (
                session.query(Project)
                .filter(Project.upload_id == upload_record.id)
                .order_by(Project.id)
                .all()
            )

        return ProjectUploadResponse(
            upload_id=upload_record.id,
            filename=upload_record.filename,
            size_bytes=upload_record.size_bytes,
            file_count=upload_record.file_count,
            created_at=upload_record.created_at,
            projects=[_project_to_summary(project) for project in projects],
        )

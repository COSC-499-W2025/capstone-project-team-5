"""Project routes for the API."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from capstone_project_team_5.api.schemas.projects import (
    ProjectAnalysisResult,
    ProjectAnalysisSkipped,
    ProjectsAnalyzeAllResponse,
    ProjectSummary,
    ProjectUpdateRequest,
    ProjectUploadResponse,
    ScoreConfig,
)
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import ArtifactSource, Project, UploadRecord
from capstone_project_team_5.models.upload import DetectedProject, InvalidZipError
from capstone_project_team_5.services.content_store import (
    compute_project_file_count,
    compute_project_fingerprint,
    ingest_zip,
    load_analysis_cache,
    load_manifest,
    materialize_project_tree,
    write_analysis_cache,
)
from capstone_project_team_5.services.incremental_upload import find_matching_projects
from capstone_project_team_5.services.project_thumbnail import (
    clear_project_thumbnail,
    get_project_thumbnail_path,
    get_thumbnail_media_type,
    has_project_thumbnail,
    set_project_thumbnail,
)
from capstone_project_team_5.services.upload import inspect_zip
from capstone_project_team_5.services.upload_storage import get_upload_zip_path, store_upload_zip
from capstone_project_team_5.workflows.analysis_pipeline import analyze_projects_structured

router = APIRouter(prefix="/projects", tags=["projects"])


_score_config: ScoreConfig = ScoreConfig()


def _project_to_summary(project: Project) -> ProjectSummary:
    has_thumbnail = has_project_thumbnail(project.id)
    thumbnail_url = f"/api/projects/{project.id}/thumbnail" if has_thumbnail else None
    return ProjectSummary(
        id=project.id,
        name=project.name,
        rel_path=project.rel_path,
        file_count=project.file_count,
        has_git_repo=project.has_git_repo,
        is_collaborative=project.is_collaborative,
        is_showcase=bool(getattr(project, "is_showcase", False)),
        thumbnail_url=thumbnail_url,
        has_thumbnail=has_thumbnail,
        importance_rank=project.importance_rank,
        importance_score=project.importance_score,
        user_role=project.user_role,
        user_contribution_percentage=project.user_contribution_percentage,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _build_consent_tool(use_ai: bool) -> ConsentTool:
    tool = ConsentTool()
    if use_ai:
        tool.use_external_services = True
        tool.external_services = {"Gemini": {"allowed": True}}
    return tool


def _get_ordered_uploads(session: Session, upload_ids: list[int]) -> list[UploadRecord]:
    if not upload_ids:
        return []
    return (
        session.query(UploadRecord)
        .filter(UploadRecord.id.in_(upload_ids))
        .order_by(UploadRecord.created_at.asc())
        .all()
    )


def _get_project_upload_ids(session: Session, project: Project) -> list[int]:
    upload_ids = {project.upload_id}
    for artifact in project.artifact_sources:
        upload_ids.add(artifact.upload_id)
    uploads = _get_ordered_uploads(session, list(upload_ids))
    return [upload.id for upload in uploads]


def _ensure_manifests(session: Session, upload_ids: list[int]) -> None:
    uploads = _get_ordered_uploads(session, upload_ids)
    for upload in uploads:
        if load_manifest(upload.id) is not None:
            continue
        zip_path = get_upload_zip_path(upload.id, upload.filename)
        if not zip_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stored upload archive not found.",
            )
        try:
            ingest_zip(zip_path, upload.id)
        except InvalidZipError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stored upload archive is invalid.",
            ) from exc


def _analyze_project_from_store(
    project: Project, upload_ids: list[int], use_ai: bool
) -> tuple[ProjectAnalysisResult, str]:
    consent_tool = _build_consent_tool(use_ai)
    file_count = compute_project_file_count(project.rel_path, upload_ids)
    detected = [
        DetectedProject(
            name=project.name,
            rel_path=project.rel_path,
            has_git_repo=project.has_git_repo,
            file_count=file_count,
        )
    ]
    with TemporaryDirectory() as temp_dir:
        extract_root = Path(temp_dir)
        materialize_project_tree(project.rel_path, upload_ids, extract_root)
        results = analyze_projects_structured(extract_root, detected, consent_tool)
    analysis_map = {(item["name"], item["rel_path"]): item for item in results}
    analysis = analysis_map.get((project.name, project.rel_path))
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project analysis failed.",
        )
    response = _analysis_to_response(project.id, analysis)
    fingerprint = compute_project_fingerprint(project.rel_path, upload_ids)
    return response, fingerprint


def _analysis_to_response(project_id: int, analysis: dict[str, Any]) -> ProjectAnalysisResult:
    return ProjectAnalysisResult(
        id=project_id,
        name=str(analysis["name"]),
        rel_path=str(analysis["rel_path"]),
        language=str(analysis["language"]),
        framework=analysis.get("framework"),
        other_languages=list(analysis.get("other_languages", [])),
        practices=list(analysis.get("practices", [])),
        tools=list(analysis.get("tools", [])),
        duration=str(analysis.get("duration", "")),
        collaborators_display=str(analysis.get("collaborators_display", "")),
        collaborators_raw=analysis["collaborators_raw"],
        file_summary=analysis["file_summary"],
        contribution=analysis["contribution"],
        contribution_summary=str(analysis.get("contribution_summary", "")),
        importance_score=float(analysis.get("score", 0.0)),
        score_breakdown=analysis.get("score_breakdown", {}),
        ai_bullets=list(analysis.get("ai_bullets", [])),
        ai_warning=analysis.get("ai_warning"),
        resume_bullets=list(analysis.get("resume_bullets", [])),
        resume_bullet_source=str(analysis.get("resume_bullet_source", "Local")),
        skill_timeline=list(analysis.get("skill_timeline", [])),
        git=analysis["git"],
        user_role=analysis.get("user_role"),
        user_contribution_percentage=analysis.get("user_contribution_percentage"),
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
        for field, value in updates.items():
            setattr(project, field, value)

        session.flush()
        session.refresh(project)
        return _project_to_summary(project)


@router.put(
    "/{project_id}/thumbnail",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Upload a project thumbnail",
    description="Upload an image thumbnail for a project by ID.",
    responses={
        400: {"description": "Invalid thumbnail upload"},
        404: {"description": "Project not found"},
    },
)
async def upload_project_thumbnail(
    project_id: int,
    file: Annotated[UploadFile, File(description="Thumbnail image file")],
) -> Response:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

    data = await file.read()
    saved, error = set_project_thumbnail(
        project_id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
    )
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error or "Invalid thumbnail upload.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{project_id}/thumbnail",
    summary="Get a project thumbnail",
    description="Return the stored thumbnail image for a project.",
    responses={
        200: {"description": "Thumbnail image"},
        404: {"description": "Project or thumbnail not found"},
    },
)
def get_project_thumbnail(project_id: int) -> Response:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

    path = get_project_thumbnail_path(project_id)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail not found.",
        )
    media_type = get_thumbnail_media_type(path) or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.delete(
    "/{project_id}/thumbnail",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project thumbnail",
    description="Remove the stored thumbnail image for a project.",
    responses={404: {"description": "Project not found"}},
)
def delete_project_thumbnail(project_id: int) -> Response:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

    clear_project_thumbnail(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        chunk_size = 8192  # 8KB chunks

        with temp_path.open("wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)

        try:
            result, collab_flags = inspect_zip(temp_path)
        except InvalidZipError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        detected_names = [project.name for project in result.projects]
        matches = find_matching_projects(detected_names) if detected_names else {}
        ambiguous = {
            name: ids for name, ids in matches.items() if len(ids) > 1 and name in detected_names
        }
        if ambiguous:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Multiple existing projects match uploaded project names.",
                    "candidates": ambiguous,
                },
            )

        with get_session() as session:
            upload_record = UploadRecord(
                filename=result.filename,
                size_bytes=result.size_bytes,
                file_count=result.file_count,
            )
            session.add(upload_record)
            session.flush()

            try:
                store_upload_zip(upload_record.id, upload_record.filename, temp_path)
            except OSError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store upload archive.",
                ) from exc

            try:
                ingest_zip(temp_path, upload_record.id)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store upload artifacts.",
                ) from exc

            existing_match_ids = [
                ids[0] for name, ids in matches.items() if len(ids) == 1 and name in detected_names
            ]
            existing_projects: dict[int, Project] = {}
            if existing_match_ids:
                for project in (
                    session.query(Project).filter(Project.id.in_(existing_match_ids)).all()
                ):
                    existing_projects[project.id] = project

            updated_projects: list[Project] = []
            new_projects: list[Project] = []
            for detected_project in result.projects:
                match_ids = matches.get(detected_project.name, [])
                if len(match_ids) == 1:
                    existing = existing_projects.get(match_ids[0])
                    if existing is None:
                        match_ids = []

                if not match_ids:
                    new_project = Project(
                        upload_id=upload_record.id,
                        name=detected_project.name,
                        rel_path=detected_project.rel_path,
                        has_git_repo=detected_project.has_git_repo,
                        file_count=detected_project.file_count,
                        is_collaborative=collab_flags.get(detected_project.rel_path, False),
                    )
                    session.add(new_project)
                    new_projects.append(new_project)
                    continue

                existing = existing_projects[match_ids[0]]
                existing.file_count += detected_project.file_count
                session.add(
                    ArtifactSource(
                        project_id=existing.id,
                        upload_id=upload_record.id,
                        artifact_count=detected_project.file_count,
                    )
                )
                upload_ids = {existing.upload_id, upload_record.id}
                upload_ids.update(source.upload_id for source in existing.artifact_sources)
                ordered_upload_ids = [
                    upload.id for upload in _get_ordered_uploads(session, list(upload_ids))
                ]
                _ensure_manifests(session, ordered_upload_ids)
                existing.file_count = compute_project_file_count(
                    existing.rel_path, ordered_upload_ids
                )
                existing.updated_at = datetime.now(UTC)
                updated_projects.append(existing)

            session.flush()
            projects = sorted(new_projects + updated_projects, key=lambda project: project.id)

        return ProjectUploadResponse(
            upload_id=upload_record.id,
            filename=upload_record.filename,
            size_bytes=upload_record.size_bytes,
            file_count=upload_record.file_count,
            created_at=upload_record.created_at,
            projects=[_project_to_summary(project) for project in projects],
        )


@router.post(
    "/{project_id}/analyze",
    response_model=ProjectAnalysisResult,
    summary="Analyze a project",
    description="Analyze a persisted project and update its importance score.",
    responses={
        400: {"description": "Project cannot be analyzed"},
        404: {"description": "Project not found"},
        409: {"description": "Stored upload archive not found"},
    },
)
def analyze_project(
    project_id: int, use_ai: bool = False, force: bool = False
) -> ProjectAnalysisResult:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )
        if not project.rel_path.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project does not have a relative path to analyze.",
            )

        upload_ids = _get_project_upload_ids(session, project)
        if not upload_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload record not found.",
            )

        _ensure_manifests(session, upload_ids)

        fingerprint = compute_project_fingerprint(project.rel_path, upload_ids)
        cached = load_analysis_cache(project.id)
        if not force and cached and cached.get("fingerprint") == fingerprint:
            payload = cached.get("payload")
            if isinstance(payload, dict):
                return ProjectAnalysisResult(**payload)

        response, fingerprint = _analyze_project_from_store(project, upload_ids, use_ai)
        project.importance_score = response.importance_score
        project.user_role = response.user_role
        project.user_contribution_percentage = response.user_contribution_percentage
        session.flush()
        write_analysis_cache(project.id, fingerprint, response.model_dump())
        return response


@router.post(
    "/analyze",
    response_model=ProjectsAnalyzeAllResponse,
    summary="Analyze all projects",
    description="Analyze all persisted projects and update their importance scores.",
)
def analyze_all_projects(use_ai: bool = False, force: bool = False) -> ProjectsAnalyzeAllResponse:
    analyzed: list[ProjectAnalysisResult] = []
    skipped: list[ProjectAnalysisSkipped] = []

    with get_session() as session:
        projects = session.query(Project).order_by(Project.upload_id, Project.id).all()
        if not projects:
            return ProjectsAnalyzeAllResponse(analyzed=[], skipped=[])

        for project in projects:
            if not project.rel_path.strip():
                skipped.append(
                    ProjectAnalysisSkipped(
                        project_id=project.id,
                        reason="Project does not have a relative path to analyze.",
                    )
                )
                continue

            upload_ids = _get_project_upload_ids(session, project)
            if not upload_ids:
                skipped.append(
                    ProjectAnalysisSkipped(
                        project_id=project.id,
                        reason="Upload record not found.",
                    )
                )
                continue

            try:
                _ensure_manifests(session, upload_ids)
            except HTTPException as exc:
                reason = str(exc.detail) if exc.detail else "Project analysis failed."
                skipped.append(ProjectAnalysisSkipped(project_id=project.id, reason=reason))
                continue

            fingerprint = compute_project_fingerprint(project.rel_path, upload_ids)
            cached = load_analysis_cache(project.id)
            if not force and cached and cached.get("fingerprint") == fingerprint:
                skipped.append(
                    ProjectAnalysisSkipped(
                        project_id=project.id,
                        reason="Merged content fingerprint unchanged.",
                    )
                )
                continue

            try:
                response, fingerprint = _analyze_project_from_store(project, upload_ids, use_ai)
                project.importance_score = response.importance_score
                project.user_role = response.user_role
                project.user_contribution_percentage = response.user_contribution_percentage
                write_analysis_cache(project.id, fingerprint, response.model_dump())
                analyzed.append(response)
            except HTTPException as exc:
                reason = str(exc.detail) if exc.detail else "Project analysis failed."
                skipped.append(ProjectAnalysisSkipped(project_id=project.id, reason=reason))
            except Exception as exc:
                skipped.append(
                    ProjectAnalysisSkipped(
                        project_id=project.id,
                        reason=f"Project analysis failed: {exc!s}",
                    )
                )
        session.flush()

    return ProjectsAnalyzeAllResponse(analyzed=analyzed, skipped=skipped)


@router.get(
    "/config/score",
    response_model=ScoreConfig,
    summary="Get score configuration",
    description="Return the current importance score factor configuration.",
)
def get_score_config() -> ScoreConfig:
    """Return the in-memory score configuration used by some clients."""

    return _score_config


@router.put(
    "/config/score",
    response_model=ScoreConfig,
    summary="Update score configuration",
    description=(
        "Update the in-memory importance score factor configuration. "
        "This endpoint does not retroactively change stored scores."
    ),
)
def update_score_config(config: ScoreConfig) -> ScoreConfig:
    """Update and return the score factor configuration."""

    global _score_config
    _score_config = config
    return _score_config

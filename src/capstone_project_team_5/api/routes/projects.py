"""Project routes for the API."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from capstone_project_team_5.api.dependencies import get_current_username
from capstone_project_team_5.api.schemas.projects import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    CodeAnalysisUpdateRequest,
    PaginatedProjectsResponse,
    PaginationMeta,
    ProjectAnalysisResult,
    ProjectAnalysisSkipped,
    ProjectReRankRequest,
    ProjectReRankResponse,
    ProjectsAnalyzeAllResponse,
    ProjectSummary,
    ProjectUpdateRequest,
    ProjectUploadAction,
    ProjectUploadResponse,
    SavedAnalysisSummary,
    SavedProjectSummary,
    SavedUploadSummary,
    ScoreConfig,
)
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import (
    ArtifactSource,
    CodeAnalysis,
    Project,
    UploadRecord,
    User,
    UserCodeAnalysis,
)
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
from capstone_project_team_5.services.project_thumbnail import (
    clear_project_thumbnail,
    get_project_thumbnail_path,
    get_thumbnail_media_type,
    has_project_thumbnail,
    set_project_thumbnail,
)
from capstone_project_team_5.services.skill_persistence import save_skills_to_db
from capstone_project_team_5.services.upload import inspect_zip
from capstone_project_team_5.services.upload_storage import get_upload_zip_path, store_upload_zip
from capstone_project_team_5.workflows.analysis_pipeline import analyze_projects_structured

logger = logging.getLogger(__name__)

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
        role_justification=project.role_justification,
        user_role_types=project.user_role_types,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _build_consent_tool(use_ai: bool) -> ConsentTool:
    tool = ConsentTool()
    if use_ai:
        tool.use_external_services = True
        tool.external_services = {"Gemini": {"allowed": True}}
    return tool


def _parse_project_mapping(raw_mapping: str | None) -> dict[str, int]:
    """Parse optional project mapping from form data."""
    if raw_mapping is None or not raw_mapping.strip():
        return {}

    try:
        payload = json.loads(raw_mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid project_mapping JSON. Expected an object of {project_name: project_id}."
            ),
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid project_mapping payload. Expected an object of {project_name: project_id}."
            ),
        )

    parsed: dict[str, int] = {}
    for raw_name, raw_project_id in payload.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_mapping key. Project names must be non-empty strings.",
            )
        if not isinstance(raw_project_id, int) or raw_project_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project_mapping value. Project IDs must be positive integers.",
            )
        parsed[raw_name] = raw_project_id
    return parsed


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
    project: Project, upload_ids: list[int], use_ai: bool, current_username: str | None = None
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
        results = analyze_projects_structured(
            extract_root, detected, consent_tool, current_user=current_username
        )
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
        role_justification=analysis.get("role_justification"),
        user_role_types=analysis.get("user_role_types"),
    )


def _get_user_or_404(session: Session, username: str) -> User:
    """Return the requested user or raise 404."""
    user = session.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found.",
        )
    return user


def _owned_project_query(session: Session, user_id: int):
    return session.query(Project).join(UploadRecord, UploadRecord.id == Project.upload_id).filter(
        UploadRecord.user_id == user_id
    )


def _get_owned_project_or_404(session: Session, project_id: int, user_id: int) -> Project:
    project = _owned_project_query(session, user_id).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return project


def _find_matching_owned_projects(
    session: Session,
    detected_projects: list[str],
    user_id: int,
) -> dict[str, list[int]]:
    matches: dict[str, list[int]] = {}
    for project_name in detected_projects:
        normalized_name = project_name.lower()
        found_project_ids = (
            _owned_project_query(session, user_id)
            .filter(func.lower(Project.name) == normalized_name)
            .with_entities(Project.id)
            .all()
        )
        found_projects = [project_id for (project_id,) in found_project_ids]
        if found_projects:
            matches[project_name] = found_projects
    return matches


def _ensure_user_analysis_link(session: Session, project_id: int, username: str) -> None:
    """Ensure a UserCodeAnalysis link exists for the user and the project's latest analysis."""
    user = session.query(User).filter(User.username == username).first()
    if user is None:
        return
    latest = (
        session.query(CodeAnalysis)
        .filter(CodeAnalysis.project_id == project_id)
        .order_by(CodeAnalysis.id.desc())
        .first()
    )
    if latest is None:
        return
    existing = (
        session.query(UserCodeAnalysis)
        .filter(
            UserCodeAnalysis.user_id == user.id,
            UserCodeAnalysis.analysis_id == latest.id,
        )
        .first()
    )
    if existing is None:
        session.add(UserCodeAnalysis(user_id=user.id, analysis_id=latest.id))


def _build_saved_uploads_response(session: Session, username: str) -> list[SavedUploadSummary]:
    """Build the saved uploads/projects view used by the TUI retrieve flow."""
    from contextlib import suppress

    user = _get_user_or_404(session, username)
    uploads = (
        session.query(UploadRecord)
        .join(Project, Project.upload_id == UploadRecord.id)
        .join(CodeAnalysis, CodeAnalysis.project_id == Project.id)
        .join(UserCodeAnalysis, UserCodeAnalysis.analysis_id == CodeAnalysis.id)
        .filter(UserCodeAnalysis.user_id == user.id)
        .order_by(UploadRecord.created_at.desc())
        .distinct()
        .all()
    )

    saved_uploads: list[SavedUploadSummary] = []

    for upload in uploads:
        saved_projects: list[SavedProjectSummary] = []

        for project in upload.projects:
            languages: set[str] = set()
            tools: set[str] = set()
            practices: set[str] = set()
            total_loc = 0
            analyses: list[SavedAnalysisSummary] = []

            for analysis in project.code_analyses:
                link = (
                    session.query(UserCodeAnalysis)
                    .filter(
                        UserCodeAnalysis.user_id == user.id,
                        UserCodeAnalysis.analysis_id == analysis.id,
                    )
                    .first()
                )
                if link is None:
                    continue

                metrics: dict[str, Any] | None = None
                if getattr(analysis, "metrics_json", None):
                    with suppress(Exception):
                        parsed = json.loads(analysis.metrics_json)
                        if isinstance(parsed, dict):
                            metrics = parsed

                if analysis.language:
                    languages.add(analysis.language)

                if isinstance(metrics, dict):
                    metrics_language = metrics.get("language") or metrics.get("language_name")
                    if isinstance(metrics_language, str) and metrics_language:
                        languages.add(metrics_language)
                    for tool in metrics.get("tools") or []:
                        tools.add(str(tool))
                    for practice in metrics.get("practices") or []:
                        practices.add(str(practice))
                    loc = metrics.get("lines_of_code") or metrics.get("total_lines_of_code")
                    if isinstance(loc, int):
                        total_loc += loc
                    elif isinstance(loc, str) and loc.isdigit():
                        total_loc += int(loc)

                def _str_list(val: Any) -> list[str] | None:
                    if isinstance(val, list):
                        return [str(x) for x in val if x] or None
                    return None

                m = metrics or {}
                analyses.append(
                    SavedAnalysisSummary(
                        id=analysis.id,
                        language=analysis.language,
                        summary_text=analysis.summary_text,
                        resume_bullets=_str_list(m.get("resume_bullets")),
                        ai_bullets=_str_list(m.get("ai_bullets")),
                        ai_warning=m.get("ai_warning"),
                        skill_timeline=m.get("skill_timeline")
                        if isinstance(m.get("skill_timeline"), list)
                        else None,
                        score_breakdown=m.get("score_breakdown")
                        if isinstance(m.get("score_breakdown"), dict)
                        else None,
                        git=m.get("git") if isinstance(m.get("git"), dict) else None,
                        tools=_str_list(m.get("tools")),
                        practices=_str_list(m.get("practices")),
                        other_languages=_str_list(m.get("other_languages")),
                        duration=m.get("duration"),
                        user_role=m.get("user_role"),
                        user_role_types=m.get("user_role_types")
                        if isinstance(m.get("user_role_types"), dict)
                        else None,
                        user_contribution_percentage=m.get("user_contribution_percentage"),
                        role_justification=m.get("role_justification"),
                        created_at=analysis.created_at,
                    )
                )

            if not analyses:
                continue

            saved_projects.append(
                SavedProjectSummary(
                    id=project.id,
                    name=project.name,
                    rel_path=project.rel_path,
                    file_count=project.file_count,
                    importance_rank=project.importance_rank,
                    importance_score=project.importance_score,
                    user_role=project.user_role,
                    user_contribution_percentage=project.user_contribution_percentage,
                    role_justification=project.role_justification,
                    user_role_types=project.user_role_types,
                    has_git_repo=project.has_git_repo,
                    is_collaborative=project.is_collaborative,
                    is_showcase=bool(getattr(project, "is_showcase", False)),
                    start_date=project.start_date,
                    end_date=project.end_date,
                    languages=sorted(languages),
                    tools=sorted(tools),
                    practices=sorted(practices),
                    lines_of_code=total_loc if total_loc > 0 else None,
                    analyses_count=len(analyses),
                    analyses=analyses,
                )
            )

        if saved_projects:
            saved_uploads.append(
                SavedUploadSummary(
                    id=upload.id,
                    filename=upload.filename,
                    size_bytes=upload.size_bytes,
                    file_count=upload.file_count,
                    created_at=upload.created_at,
                    projects=saved_projects,
                )
            )

    return saved_uploads


@router.get(
    "/",
    response_model=PaginatedProjectsResponse,
    summary="List projects",
    description="Return all persisted projects ordered by most recently updated.",
)
def list_projects(
    current_username: Annotated[str, Depends(get_current_username)],
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=1,
        le=MAX_LIMIT,
        description=f"Maximum number of items to return (1-{MAX_LIMIT})",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of items to skip",
    ),
) -> PaginatedProjectsResponse:
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        query = _owned_project_query(session, user.id).order_by(desc(Project.updated_at))
        total = query.count()
        projects = query.offset(offset).limit(limit).all()
        return PaginatedProjectsResponse(
            items=[_project_to_summary(project) for project in projects],
            pagination=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(projects)) < total,
            ),
        )


@router.get(
    "/saved/{username}",
    response_model=list[SavedUploadSummary],
    summary="List saved uploads for a user",
    description=(
        "Return the saved uploads, projects, and analyses visible to the authenticated user. "
        "This mirrors the TUI 'Retrieve Projects' view."
    ),
    responses={
        403: {"description": "Cannot access another user's saved analyses"},
        404: {"description": "User not found"},
    },
)
def list_saved_projects(
    username: str,
    current_username: Annotated[str, Depends(get_current_username)],
) -> list[SavedUploadSummary]:
    """Return saved uploads/projects/analyses for the authenticated user."""
    if current_username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own saved analyses.",
        )

    with get_session() as session:
        return _build_saved_uploads_response(session, username)


@router.patch(
    "/{project_id}/analyses/{analysis_id}",
    response_model=SavedAnalysisSummary,
    summary="Update a saved analysis",
    description="Update the language or summary text of a specific code analysis.",
    responses={
        403: {"description": "Analysis does not belong to the authenticated user"},
        404: {"description": "Analysis not found"},
    },
)
def update_analysis(
    project_id: int,
    analysis_id: int,
    update: CodeAnalysisUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> SavedAnalysisSummary:
    """Update editable fields on a code analysis."""
    with get_session() as session:
        analysis = (
            session.query(CodeAnalysis)
            .filter(CodeAnalysis.id == analysis_id, CodeAnalysis.project_id == project_id)
            .first()
        )
        if analysis is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")

        # Verify the authenticated user owns this analysis
        user = session.query(User).filter(User.username == current_username).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not found.")
        link = (
            session.query(UserCodeAnalysis)
            .filter(
                UserCodeAnalysis.analysis_id == analysis_id, UserCodeAnalysis.user_id == user.id
            )
            .first()
        )
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own analyses.",
            )

        if update.language is not None:
            analysis.language = update.language
        if update.summary_text is not None:
            analysis.summary_text = update.summary_text
        metrics_patch = {
            k: getattr(update, k)
            for k in (
                "resume_bullets",
                "ai_bullets",
                "score_breakdown",
                "skill_timeline",
                "tools",
                "practices",
                "other_languages",
            )
            if getattr(update, k) is not None
        }
        if metrics_patch:
            try:
                metrics = json.loads(analysis.metrics_json) if analysis.metrics_json else {}
            except Exception:
                metrics = {}
            metrics.update(metrics_patch)
            analysis.metrics_json = json.dumps(metrics)

        session.flush()

        try:
            m2 = json.loads(analysis.metrics_json) if analysis.metrics_json else {}
        except Exception:
            m2 = {}

        def _sl(val: Any) -> list[str] | None:
            return [str(x) for x in val if x] or None if isinstance(val, list) else None

        return SavedAnalysisSummary(
            id=analysis.id,
            language=analysis.language,
            summary_text=analysis.summary_text,
            resume_bullets=_sl(m2.get("resume_bullets")),
            ai_bullets=_sl(m2.get("ai_bullets")),
            ai_warning=m2.get("ai_warning"),
            skill_timeline=m2.get("skill_timeline")
            if isinstance(m2.get("skill_timeline"), list)
            else None,
            score_breakdown=m2.get("score_breakdown")
            if isinstance(m2.get("score_breakdown"), dict)
            else None,
            git=m2.get("git") if isinstance(m2.get("git"), dict) else None,
            tools=_sl(m2.get("tools")),
            practices=_sl(m2.get("practices")),
            other_languages=_sl(m2.get("other_languages")),
            duration=m2.get("duration"),
            user_role=m2.get("user_role"),
            user_role_types=m2.get("user_role_types")
            if isinstance(m2.get("user_role_types"), dict)
            else None,
            user_contribution_percentage=m2.get("user_contribution_percentage"),
            role_justification=m2.get("role_justification"),
            created_at=analysis.created_at,
        )


@router.get(
    "/{project_id}",
    response_model=ProjectSummary,
    summary="Get a project",
    description="Return a single project by ID.",
    responses={404: {"description": "Project not found"}},
)
def get_project(
    project_id: int,
    current_username: Annotated[str, Depends(get_current_username)],
) -> ProjectSummary:
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        project = _get_owned_project_or_404(session, project_id, user.id)
        return _project_to_summary(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectSummary,
    summary="Update a project",
    description="Update editable fields on a project by ID.",
    responses={404: {"description": "Project not found"}},
)
def update_project(
    project_id: int,
    update: ProjectUpdateRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> ProjectSummary:
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        project = _get_owned_project_or_404(session, project_id, user.id)

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
    current_username: Annotated[str, Depends(get_current_username)],
) -> Response:
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        _get_owned_project_or_404(session, project_id, user.id)

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
def get_project_thumbnail(
    project_id: int,
    current_username: Annotated[str, Depends(get_current_username)],
) -> Response:
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        _get_owned_project_or_404(session, project_id, user.id)

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
def delete_project_thumbnail(
    project_id: int,
    current_username: Annotated[str, Depends(get_current_username)],
) -> Response:
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        _get_owned_project_or_404(session, project_id, user.id)

    clear_project_thumbnail(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Delete a project by ID.",
    responses={404: {"description": "Project not found"}},
)
def delete_project(
    project_id: int,
    current_username: Annotated[str, Depends(get_current_username)],
) -> Response:
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        project = _get_owned_project_or_404(session, project_id, user.id)
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
    current_username: Annotated[str, Depends(get_current_username)],
    file: Annotated[UploadFile, File(description="ZIP archive containing project files")],
    project_mapping: Annotated[
        str | None,
        Form(
            description=(
                "Optional JSON object mapping uploaded project names to existing project IDs. "
                "Use this to explicitly resolve ambiguous project-name matches."
            )
        ),
    ] = None,
) -> ProjectUploadResponse:
    filename = Path(file.filename or "upload.zip").name
    if not filename.lower().endswith(".zip"):
        filename = f"{filename}.zip"
    requested_mapping = _parse_project_mapping(project_mapping)

    t_total = time.perf_counter()
    logger.info("[upload] ▶ started  file=%s", filename)

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / filename
        chunk_size = 8192  # 8KB chunks

        t0 = time.perf_counter()
        with temp_path.open("wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
        size_kb = temp_path.stat().st_size / 1024
        logger.info(
            "[upload] ✔ streamed to disk  %.1f KB  (%.3fs)", size_kb, time.perf_counter() - t0
        )

        t0 = time.perf_counter()
        try:
            result, collab_flags, _project_dates = inspect_zip(temp_path)
        except InvalidZipError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        logger.info(
            "[upload] ✔ inspect_zip  projects=%d  files=%d  (%.3fs)",
            len(result.projects),
            result.file_count,
            time.perf_counter() - t0,
        )

        detected_names = [project.name for project in result.projects]
        unknown_mapped_names = sorted(set(requested_mapping.keys()) - set(detected_names))
        if unknown_mapped_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": (
                        "project_mapping contains names that were not detected in this upload."
                    ),
                    "unknown_project_names": unknown_mapped_names,
                },
            )
        with get_session() as session:
            user = _get_user_or_404(session, current_username)
            matches = (
                _find_matching_owned_projects(session, detected_names, user.id)
                if detected_names
                else {}
            )
            ambiguous = {
                name: ids
                for name, ids in matches.items()
                if len(ids) > 1 and name in detected_names and name not in requested_mapping
            }
            if ambiguous:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Multiple existing projects match uploaded project names.",
                        "candidates": ambiguous,
                    },
                )

            upload_record = UploadRecord(
                user_id=user.id,
                filename=result.filename,
                size_bytes=result.size_bytes,
                file_count=result.file_count,
            )
            session.add(upload_record)
            session.flush()

            t0 = time.perf_counter()
            try:
                store_upload_zip(upload_record.id, upload_record.filename, temp_path)
            except OSError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store upload archive.",
                ) from exc
            logger.info("[upload] ✔ store_upload_zip  (%.3fs)", time.perf_counter() - t0)

            t0 = time.perf_counter()
            try:
                ingest_zip(temp_path, upload_record.id)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to store upload artifacts.",
                ) from exc
            logger.info("[upload] ✔ ingest_zip  (%.3fs)", time.perf_counter() - t0)

            existing_match_ids = [
                ids[0]
                for name, ids in matches.items()
                if len(ids) == 1 and name in detected_names and name not in requested_mapping
            ]
            existing_match_ids.extend(requested_mapping.values())
            existing_projects: dict[int, Project] = {}
            if existing_match_ids:
                for project in (
                    session.query(Project).filter(Project.id.in_(existing_match_ids)).all()
                ):
                    existing_projects[project.id] = project
            missing_mapped_ids = sorted(
                project_id
                for project_id in set(requested_mapping.values())
                if project_id not in existing_projects
            )
            if missing_mapped_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "project_mapping references unknown project IDs.",
                        "unknown_project_ids": missing_mapped_ids,
                    },
                )

            updated_projects: list[Project] = []
            new_projects: list[Project] = []
            upload_actions: list[dict[str, Any]] = []
            for detected_project in result.projects:
                mapped_project_id = requested_mapping.get(detected_project.name)
                if mapped_project_id is not None:
                    match_ids = [mapped_project_id]
                else:
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
                    upload_actions.append(
                        {
                            "project": new_project,
                            "project_name": detected_project.name,
                            "action": "created",
                            "merged_into_project_id": None,
                        }
                    )
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
                upload_actions.append(
                    {
                        "project": existing,
                        "project_name": detected_project.name,
                        "action": "merged",
                        "merged_into_project_id": existing.id,
                    }
                )

            session.flush()
            projects = sorted(new_projects + updated_projects, key=lambda project: project.id)
            actions = [
                ProjectUploadAction(
                    project_id=int(action["project"].id),
                    project_name=str(action["project_name"]),
                    action=str(action["action"]),
                    merged_into_project_id=action["merged_into_project_id"],
                )
                for action in upload_actions
            ]
            created_count = sum(1 for action in actions if action.action == "created")
            merged_count = sum(1 for action in actions if action.action == "merged")

        logger.info(
            "[upload] ✔ done  created=%d merged=%d  total=%.3fs",
            created_count,
            merged_count,
            time.perf_counter() - t_total,
        )
        return ProjectUploadResponse(
            upload_id=upload_record.id,
            filename=upload_record.filename,
            size_bytes=upload_record.size_bytes,
            file_count=upload_record.file_count,
            created_at=upload_record.created_at,
            projects=[_project_to_summary(project) for project in projects],
            actions=actions,
            created_count=created_count,
            merged_count=merged_count,
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
    project_id: int,
    current_username: Annotated[str, Depends(get_current_username)],
    use_ai: bool = False,
    force: bool = False,
) -> ProjectAnalysisResult:
    # Phase 1: load project data and handle cache — close session before running
    # analysis so we don't hold a SQLite shared lock that would prevent
    # save_code_analysis_to_db (which opens its own session) from writing.
    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        project = _get_owned_project_or_404(session, project_id, user.id)
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
                cached_response = ProjectAnalysisResult(**payload)
                save_skills_to_db(
                    session,
                    project.id,
                    cached_response.tools,
                    cached_response.practices,
                )
                _ensure_user_analysis_link(session, project.id, current_username)
                return cached_response
        # expire_on_commit=False means project attributes survive session close

    # Phase 2: run analysis with no session open so save_code_analysis_to_db
    # can acquire its own write lock without contention.
    response, fingerprint = _analyze_project_from_store(
        project, upload_ids, use_ai, current_username=current_username
    )

    # Phase 3: persist results in a fresh session (can now see the CodeAnalysis
    # row that save_code_analysis_to_db committed in phase 2).
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        if project is not None:
            project.importance_score = response.importance_score
            project.user_role = response.user_role
            project.user_contribution_percentage = response.user_contribution_percentage
            project.role_justification = response.role_justification
            project.user_role_types = response.user_role_types
            if response.user_role_types is not None:
                flag_modified(project, "user_role_types")
        save_skills_to_db(session, project_id, response.tools, response.practices)

        # Enrich the CodeAnalysis record created by save_code_analysis_to_db
        # with the full API response data (bullets, git, score breakdown, etc.).
        code_analysis = (
            session.query(CodeAnalysis)
            .filter(CodeAnalysis.project_id == project_id)
            .order_by(CodeAnalysis.id.desc())
            .first()
        )
        if code_analysis is not None:
            code_analysis.metrics_json = json.dumps(
                {
                    "language": response.language,
                    "framework": response.framework,
                    "other_languages": list(response.other_languages or []),
                    "tools": list(response.tools or []),
                    "practices": list(response.practices or []),
                    "score_breakdown": response.score_breakdown or {},
                    "resume_bullets": list(response.resume_bullets or []),
                    "ai_bullets": list(response.ai_bullets or []),
                    "ai_warning": response.ai_warning,
                    "skill_timeline": [
                        e.model_dump() if hasattr(e, "model_dump") else e
                        for e in (response.skill_timeline or [])
                    ],
                    "git": response.git.model_dump() if response.git else None,
                    "duration": response.duration,
                    "collaborators_display": response.collaborators_display,
                    "contribution_summary": response.contribution_summary,
                    "importance_score": response.importance_score,
                    "user_role": response.user_role,
                    "user_contribution_percentage": response.user_contribution_percentage,
                    "role_justification": response.role_justification,
                    "user_role_types": response.user_role_types,
                }
            )

        _ensure_user_analysis_link(session, project_id, current_username)

    write_analysis_cache(project_id, fingerprint, response.model_dump())
    return response


@router.post(
    "/analyze",
    response_model=ProjectsAnalyzeAllResponse,
    summary="Analyze all projects",
    description="Analyze all persisted projects and update their importance scores.",
)
def analyze_all_projects(
    current_username: Annotated[str, Depends(get_current_username)],
    use_ai: bool = False,
    force: bool = False,
) -> ProjectsAnalyzeAllResponse:
    analyzed: list[ProjectAnalysisResult] = []
    skipped: list[ProjectAnalysisSkipped] = []

    with get_session() as session:
        user = _get_user_or_404(session, current_username)
        projects = _owned_project_query(session, user.id).order_by(Project.upload_id, Project.id).all()
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
                payload = cached.get("payload")
                if isinstance(payload, dict):
                    try:
                        cached_response = ProjectAnalysisResult(**payload)
                    except (TypeError, ValueError):
                        cached_response = None
                    if cached_response is not None:
                        save_skills_to_db(
                            session,
                            project.id,
                            cached_response.tools,
                            cached_response.practices,
                        )
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
                save_skills_to_db(session, project.id, response.tools, response.practices)
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


@router.post(
    "/rerank",
    response_model=ProjectReRankResponse,
    summary="Batch update project importance ranks",
    description=(
        "Update importance ranks for multiple projects in a single operation. "
        "This allows users to customize the display order of their projects. "
        "Ranks should be unique positive integers."
    ),
    responses={
        400: {
            "description": "Invalid rank values (duplicates, negatives, or non-existent projects)"
        },
    },
)
def rerank_projects(request: ProjectReRankRequest) -> ProjectReRankResponse:
    """Batch update importance ranks for projects.

    Validates that:
    - All projects exist
    - Ranks are positive integers
    - No duplicate ranks in the request

    Args:
        request: List of project_id and importance_rank pairs

    Returns:
        ProjectReRankResponse with updated project count and summaries

    Raises:
        HTTPException 400: If validation fails
        HTTPException 404: If any project is not found
    """
    if not request.rankings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rankings list cannot be empty",
        )

    # Validate unique ranks
    ranks = [r.importance_rank for r in request.rankings]
    if len(ranks) != len(set(ranks)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate ranks are not allowed",
        )

    # Validate positive ranks
    if any(r < 1 for r in ranks):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All ranks must be positive integers (>= 1)",
        )

    # Validate unique project IDs
    project_ids = [r.project_id for r in request.rankings]
    if len(project_ids) != len(set(project_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate project IDs are not allowed",
        )

    with get_session() as session:
        # Validate all projects exist
        projects = session.query(Project).filter(Project.id.in_(project_ids)).all()
        if len(projects) != len(project_ids):
            found_ids = {p.id for p in projects}
            missing_ids = set(project_ids) - found_ids
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Projects not found: {sorted(missing_ids)}",
            )

        # Build project lookup map to avoid N queries in the loop
        project_map = {p.id: p for p in projects}

        # Update ranks
        updated_projects = []
        for rank_update in request.rankings:
            project = project_map.get(rank_update.project_id)
            if project:
                project.importance_rank = rank_update.importance_rank
                updated_projects.append(project)

        session.flush()

        # Refresh and return
        for project in updated_projects:
            session.refresh(project)

        return ProjectReRankResponse(
            updated=len(updated_projects),
            projects=[_project_to_summary(p) for p in updated_projects],
        )

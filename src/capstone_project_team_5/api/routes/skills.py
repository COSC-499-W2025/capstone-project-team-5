"""Skills routes for the API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from capstone_project_team_5.api.schemas.skills import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    PaginatedSkillsResponse,
    PaginationMeta,
    ProjectSkillsResponse,
    SkillResponse,
)
from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, ProjectSkill, Skill

router = APIRouter(prefix="/projects/{project_id}/skills", tags=["skills"])
global_router = APIRouter(prefix="/skills", tags=["skills"])


def _skill_to_response(skill: Skill) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        skill_type=skill.skill_type,
    )


def _get_project_or_404(session: object, project_id: int) -> Project:
    """Get a project by ID or raise 404 if not found."""
    project = session.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return project


def _build_skills_query(
    session: object, project_id: int, skill_type: SkillType | None = None
) -> object:
    """Build a query for skills of a project, optionally filtered by type."""
    query = (
        session.query(Skill)
        .join(ProjectSkill, ProjectSkill.skill_id == Skill.id)
        .filter(ProjectSkill.project_id == project_id)
    )
    if skill_type is not None:
        query = query.filter(Skill.skill_type == skill_type)
    return query.order_by(Skill.name)


def _get_skills_paginated(
    session: object,
    project_id: int,
    skill_type: SkillType | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[list[Skill], int]:
    """Query skills for a project with pagination. Returns (skills, total_count)."""
    query = _build_skills_query(session, project_id, skill_type)
    total = query.count()
    skills = query.offset(offset).limit(limit).all()
    return skills, total


@router.get(
    "/",
    response_model=ProjectSkillsResponse,
    summary="Get project skills",
    description="Return all skills (tools and practices) for a project.",
    responses={404: {"description": "Project not found"}},
)
def get_project_skills(project_id: int) -> ProjectSkillsResponse:
    with get_session() as session:
        _get_project_or_404(session, project_id)

        tools_query = _build_skills_query(session, project_id, SkillType.TOOL)
        practices_query = _build_skills_query(session, project_id, SkillType.PRACTICE)

        tools = tools_query.all()
        practices = practices_query.all()

        return ProjectSkillsResponse(
            project_id=project_id,
            tools=[_skill_to_response(s) for s in tools],
            practices=[_skill_to_response(s) for s in practices],
            tools_count=len(tools),
            practices_count=len(practices),
        )


@router.get(
    "/tools",
    response_model=PaginatedSkillsResponse,
    summary="Get project tools",
    description="Return only tools for a project with pagination.",
    responses={404: {"description": "Project not found"}},
)
def get_project_tools(
    project_id: int,
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
) -> PaginatedSkillsResponse:
    with get_session() as session:
        _get_project_or_404(session, project_id)
        tools, total = _get_skills_paginated(session, project_id, SkillType.TOOL, limit, offset)
        return PaginatedSkillsResponse(
            items=[_skill_to_response(s) for s in tools],
            pagination=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(tools)) < total,
            ),
        )


@router.get(
    "/practices",
    response_model=PaginatedSkillsResponse,
    summary="Get project practices",
    description="Return only practices for a project with pagination.",
    responses={404: {"description": "Project not found"}},
)
def get_project_practices(
    project_id: int,
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
) -> PaginatedSkillsResponse:
    with get_session() as session:
        _get_project_or_404(session, project_id)
        practices, total = _get_skills_paginated(
            session, project_id, SkillType.PRACTICE, limit, offset
        )
        return PaginatedSkillsResponse(
            items=[_skill_to_response(s) for s in practices],
            pagination=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(practices)) < total,
            ),
        )


@global_router.get(
    "/",
    response_model=PaginatedSkillsResponse,
    summary="List all skills",
    description="Return all skills across all projects, optionally filtered by type.",
)
def get_all_skills(
    skill_type: SkillType | None = Query(  # noqa: B008
        default=None,
        description="Filter by skill type (tool or practice)",
    ),
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
) -> PaginatedSkillsResponse:
    with get_session() as session:
        query = session.query(Skill)
        if skill_type is not None:
            query = query.filter(Skill.skill_type == skill_type)
        query = query.order_by(Skill.name)
        total = query.count()
        skills = query.offset(offset).limit(limit).all()
        return PaginatedSkillsResponse(
            items=[_skill_to_response(s) for s in skills],
            pagination=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(skills)) < total,
            ),
        )

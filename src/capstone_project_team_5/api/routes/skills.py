"""Skills routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from capstone_project_team_5.api.dependencies import get_current_username, get_optional_username
from capstone_project_team_5.api.schemas.skills import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    PaginatedSkillsResponse,
    PaginationMeta,
    ProjectSkillsResponse,
    SkillResponse,
    UpdateProficiencyRequest,
)
from capstone_project_team_5.constants.skill_detection_constants import ProficiencyLevel, SkillType
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, ProjectSkill, Skill, User, UserSkill

router = APIRouter(prefix="/projects/{project_id}/skills", tags=["skills"])
global_router = APIRouter(prefix="/skills", tags=["skills"])


def _skill_to_response(
    skill: Skill,
    proficiency_level: ProficiencyLevel | None = None,
) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        name=skill.name,
        skill_type=skill.skill_type,
        proficiency_level=proficiency_level,
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
    description="Return all skills in the catalog, optionally filtered by type.",
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
    current_username: str | None = Depends(get_optional_username),  # noqa: B008
) -> PaginatedSkillsResponse:
    with get_session() as session:
        query = session.query(Skill)
        if skill_type is not None:
            query = query.filter(Skill.skill_type == skill_type)
        query = query.order_by(Skill.name)
        total = query.count()
        skills = query.offset(offset).limit(limit).all()

        # Build proficiency lookup for authenticated users
        prof_map: dict[int, UserSkill] = {}
        if current_username:
            user = session.query(User).filter(User.username == current_username).first()
            if user:
                skill_ids = [s.id for s in skills]
                if skill_ids:
                    user_skills = (
                        session.query(UserSkill)
                        .filter(UserSkill.user_id == user.id, UserSkill.skill_id.in_(skill_ids))
                        .all()
                    )
                    prof_map = {us.skill_id: us for us in user_skills}

        items = [
            _skill_to_response(
                s,
                proficiency_level=prof_map[s.id].proficiency_level if s.id in prof_map else None,
            )
            for s in skills
        ]

        return PaginatedSkillsResponse(
            items=items,
            pagination=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(skills)) < total,
            ),
        )


@global_router.patch(
    "/{skill_id}/proficiency",
    response_model=SkillResponse,
    summary="Update skill proficiency",
    description="Set or clear the proficiency level for a skill.",
    responses={401: {"description": "Not authenticated"}, 404: {"description": "Skill not found"}},
)
def update_skill_proficiency(
    skill_id: int,
    body: UpdateProficiencyRequest,
    current_username: Annotated[str, Depends(get_current_username)],
) -> SkillResponse:
    with get_session() as session:
        skill = session.query(Skill).filter(Skill.id == skill_id).first()
        if skill is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")

        user = session.query(User).filter(User.username == current_username).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        us = session.query(UserSkill).filter_by(user_id=user.id, skill_id=skill.id).first()

        if body.proficiency_level is not None:
            if us is None:
                us = UserSkill(
                    user_id=user.id,
                    skill_id=skill.id,
                    proficiency_level=body.proficiency_level,
                )
                session.add(us)
            else:
                us.proficiency_level = body.proficiency_level
            session.flush()
            return _skill_to_response(skill, us.proficiency_level)

        # Clear proficiency
        if us is not None:
            session.delete(us)
            session.flush()
        return _skill_to_response(skill)

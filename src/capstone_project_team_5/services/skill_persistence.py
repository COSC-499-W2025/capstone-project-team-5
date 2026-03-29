"""
Service for persisting detected skills to the database.

This module provides functions to save skills (tools and practices)
to the Skill and ProjectSkill tables.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from capstone_project_team_5.constants.skill_detection_constants import SkillType


def save_skills_to_db(
    session: Session,
    project_id: int,
    tools: set[str],
    practices: set[str],
) -> None:
    """Save detected skills to the Skill and ProjectSkill tables.

    Uses batch operations to minimize database queries:
    1. Fetches all existing skills in one query
    2. Bulk inserts new skills
    3. Fetches existing project-skill links in one query
    4. Bulk inserts new project-skill associations

    Args:
        session: SQLAlchemy session
        project_id: ID of the project to associate skills with
        tools: Set of detected tool names
        practices: Set of detected practice names
    """
    from capstone_project_team_5.data.models import ProjectSkill, Skill

    # Build list of (name, skill_type) tuples, filtering empty strings
    skill_entries: list[tuple[str, SkillType]] = []
    for tool in tools:
        if tool and tool.strip():
            skill_entries.append((tool.strip(), SkillType.TOOL))
    for practice in practices:
        if practice and practice.strip():
            skill_entries.append((practice.strip(), SkillType.PRACTICE))

    if not skill_entries:
        return

    # Get all skill names we need
    skill_names = {name for name, _ in skill_entries}

    # Batch fetch existing skills (1 query instead of N)
    existing_skills = session.query(Skill).filter(Skill.name.in_(skill_names)).all()
    existing_skill_map = {s.name: s for s in existing_skills}

    # Insert new skills that don't exist
    new_skills = []
    for name, skill_type in skill_entries:
        if name not in existing_skill_map:
            new_skill = Skill(name=name, skill_type=skill_type)
            new_skills.append(new_skill)
            existing_skill_map[name] = new_skill  # Track for later

    if new_skills:
        session.add_all(new_skills)
        session.flush()  # Get IDs for new skills

    # Collect all skill IDs we need to link
    skill_ids = [existing_skill_map[name].id for name, _ in skill_entries]

    # Batch fetch existing project-skill links (1 query instead of N)
    existing_links = (
        session.query(ProjectSkill.skill_id)
        .filter(
            ProjectSkill.project_id == project_id,
            ProjectSkill.skill_id.in_(skill_ids),
        )
        .all()
    )
    existing_link_ids = {link.skill_id for link in existing_links}

    # Bulk insert new project-skill associations
    new_links = [
        ProjectSkill(project_id=project_id, skill_id=skill_id)
        for skill_id in skill_ids
        if skill_id not in existing_link_ids
    ]
    if new_links:
        session.add_all(new_links)

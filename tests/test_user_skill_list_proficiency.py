"""Tests for proficiency in chronological skills output and resume formatting."""

from __future__ import annotations

import uuid

from capstone_project_team_5.constants.skill_detection_constants import (
    ProficiencyLevel,
    SkillType,
)
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import (
    Project,
    ProjectSkill,
    Skill,
    UploadRecord,
    User,
    UserSkill,
)
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.user_code_analysis import UserCodeAnalysis
from capstone_project_team_5.services.user_skill_list import get_chronological_skills


def test_chronological_skills_includes_proficiency(api_db: None) -> None:
    """get_chronological_skills should include proficiency_level in each dict."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        proj = Project(upload_id=upload.id, name=f"P_{uid}", rel_path=f"p/{uid}", file_count=1)
        session.add(proj)
        session.flush()

        skill = Skill(name=f"Python_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        session.add(ProjectSkill(project_id=proj.id, skill_id=skill.id))

        ca = CodeAnalysis(project_id=proj.id, language="Python", metrics_json="{}")
        session.add(ca)
        session.flush()

        uca = UserCodeAnalysis(user_id=user.id, analysis_id=ca.id)
        session.add(uca)
        session.flush()

        session.add(
            UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                proficiency_level=ProficiencyLevel.EXPERT,
            )
        )
        session.flush()

        skills = get_chronological_skills(session, user.id)
        assert len(skills) >= 1
        py_skill = next(s for s in skills if s["skill_name"] == f"Python_{uid}")
        assert py_skill["proficiency_level"] == ProficiencyLevel.EXPERT


def test_chronological_skills_null_proficiency_when_no_user_skill(
    api_db: None,
) -> None:
    """Skills without a UserSkill row should have proficiency_level=None."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        proj = Project(upload_id=upload.id, name=f"P_{uid}", rel_path=f"p/{uid}", file_count=1)
        session.add(proj)
        session.flush()

        skill = Skill(name=f"Go_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        session.add(ProjectSkill(project_id=proj.id, skill_id=skill.id))

        ca = CodeAnalysis(project_id=proj.id, language="Go", metrics_json="{}")
        session.add(ca)
        session.flush()

        uca = UserCodeAnalysis(user_id=user.id, analysis_id=ca.id)
        session.add(uca)
        session.flush()

        skills = get_chronological_skills(session, user.id)
        go_skill = next(s for s in skills if s["skill_name"] == f"Go_{uid}")
        assert go_skill["proficiency_level"] is None


def test_build_skills_groups_by_proficiency_level() -> None:
    """_build_skills should group skills by proficiency level."""
    from capstone_project_team_5.services.resume_generator import _build_skills

    skill_list = [
        {"skill_name": "Python", "skill_type": SkillType.TOOL, "proficiency_level": "expert"},
        {"skill_name": "React", "skill_type": SkillType.TOOL, "proficiency_level": None},
        {"skill_name": "TDD", "skill_type": SkillType.PRACTICE, "proficiency_level": "proficient"},
        {"skill_name": "Docker", "skill_type": SkillType.TOOL, "proficiency_level": "expert"},
    ]
    result = _build_skills(skill_list)
    assert result["expert"] == ["Python", "Docker"]
    assert result["proficient"] == ["TDD"]
    assert result["other"] == ["React"]
    assert "intermediate" not in result
    assert "beginner" not in result

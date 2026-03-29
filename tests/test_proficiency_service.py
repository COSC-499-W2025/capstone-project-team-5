"""Tests for proficiency auto-detection service."""

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
from capstone_project_team_5.services.proficiency_service import compute_and_save_proficiency


def _make_project_with_analysis(
    session, upload_id: int, user_id: int, uid: str, index: int
) -> Project:
    """Helper: create a project with CodeAnalysis + UserCodeAnalysis linking it to the user."""
    p = Project(
        upload_id=upload_id,
        name=f"Proj_{index}_{uid}",
        rel_path=f"p/{index}/{uid}",
        file_count=1,
    )
    session.add(p)
    session.flush()

    ca = CodeAnalysis(project_id=p.id, language="Python", metrics_json="{}")
    session.add(ca)
    session.flush()

    uca = UserCodeAnalysis(user_id=user_id, analysis_id=ca.id)
    session.add(uca)
    session.flush()

    return p


def test_single_project_yields_beginner(api_db: None) -> None:
    """A skill used in 1 project should be rated Beginner."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        skill = Skill(name=f"Python_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        proj = _make_project_with_analysis(session, upload.id, user.id, uid, 0)
        session.add(ProjectSkill(project_id=proj.id, skill_id=skill.id))
        session.flush()

        compute_and_save_proficiency(session, user.id)

        us = session.query(UserSkill).filter_by(user_id=user.id, skill_id=skill.id).one()
        assert us.proficiency_level == ProficiencyLevel.BEGINNER
        assert us.is_manual_override is False


def test_three_projects_yields_intermediate(api_db: None) -> None:
    """A skill used in 3 projects should be rated Intermediate."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        skill = Skill(name=f"React_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        for i in range(3):
            proj = _make_project_with_analysis(session, upload.id, user.id, uid, i)
            session.add(ProjectSkill(project_id=proj.id, skill_id=skill.id))
        session.flush()

        compute_and_save_proficiency(session, user.id)

        us = session.query(UserSkill).filter_by(user_id=user.id, skill_id=skill.id).one()
        assert us.proficiency_level == ProficiencyLevel.INTERMEDIATE


def test_five_projects_yields_proficient(api_db: None) -> None:
    """A skill used in 5 projects should be rated Proficient."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        skill = Skill(name=f"Docker_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        for i in range(5):
            proj = _make_project_with_analysis(session, upload.id, user.id, uid, i)
            session.add(ProjectSkill(project_id=proj.id, skill_id=skill.id))
        session.flush()

        compute_and_save_proficiency(session, user.id)

        us = session.query(UserSkill).filter_by(user_id=user.id, skill_id=skill.id).one()
        assert us.proficiency_level == ProficiencyLevel.PROFICIENT


def test_six_projects_yields_expert(api_db: None) -> None:
    """A skill used in 6+ projects should be rated Expert."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        skill = Skill(name=f"Git_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        for i in range(6):
            proj = _make_project_with_analysis(session, upload.id, user.id, uid, i)
            session.add(ProjectSkill(project_id=proj.id, skill_id=skill.id))
        session.flush()

        compute_and_save_proficiency(session, user.id)

        us = session.query(UserSkill).filter_by(user_id=user.id, skill_id=skill.id).one()
        assert us.proficiency_level == ProficiencyLevel.EXPERT


def test_manual_override_not_overwritten(api_db: None) -> None:
    """A manually set proficiency should not be changed by auto-detection."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        skill = Skill(name=f"Rust_{uid}", skill_type=SkillType.TOOL)
        session.add(skill)
        session.flush()

        # Only 1 project → auto would be Beginner
        proj = _make_project_with_analysis(session, upload.id, user.id, uid, 0)
        session.add(ProjectSkill(project_id=proj.id, skill_id=skill.id))
        session.flush()

        # But user manually set Expert
        session.add(
            UserSkill(
                user_id=user.id,
                skill_id=skill.id,
                proficiency_level=ProficiencyLevel.EXPERT,
                is_manual_override=True,
            )
        )
        session.flush()

        compute_and_save_proficiency(session, user.id)

        us = session.query(UserSkill).filter_by(user_id=user.id, skill_id=skill.id).one()
        assert us.proficiency_level == ProficiencyLevel.EXPERT
        assert us.is_manual_override is True


def test_save_skills_triggers_proficiency_computation(api_db: None) -> None:
    """After saving skills with user_id, proficiency should be auto-computed."""
    uid = uuid.uuid4().hex[:8]
    with get_session() as session:
        user = User(username=f"u_{uid}", password_hash="x")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename=f"f_{uid}.zip", size_bytes=1, file_count=1)
        session.add(upload)
        session.flush()

        proj = _make_project_with_analysis(session, upload.id, user.id, uid, 0)

        from capstone_project_team_5.services.skill_persistence import save_skills_to_db

        save_skills_to_db(session, proj.id, {f"Python_{uid}"}, set(), user_id=user.id)

        us = session.query(UserSkill).filter_by(user_id=user.id).first()
        assert us is not None
        assert us.proficiency_level == ProficiencyLevel.BEGINNER

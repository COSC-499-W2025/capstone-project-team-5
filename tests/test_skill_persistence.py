from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy.orm import Session

from capstone_project_team_5.data.db import get_session, init_db
from capstone_project_team_5.data.models import Project, ProjectSkill, Skill, UploadRecord
from capstone_project_team_5.services.skill_persistence import save_skills_to_db


@contextmanager
def _temporary_db_url(url: str) -> Iterator[None]:
    original = os.getenv("DB_URL")
    os.environ["DB_URL"] = url
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DB_URL", None)
        else:
            os.environ["DB_URL"] = original


@pytest.fixture
def in_memory_db() -> Iterator[None]:
    with _temporary_db_url("sqlite:///:memory:"):
        import capstone_project_team_5.data.db as app_db

        app_db._engine = None
        app_db._SessionLocal = None
        init_db()
        yield


@pytest.fixture
def session_with_project(in_memory_db: None) -> Iterator[tuple[Session, int]]:
    """Create a session with a project and yield (session, project_id)."""
    with get_session() as session:
        upload = UploadRecord(filename="test.zip", size_bytes=100, file_count=1)
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name="TestProject",
            rel_path="test/path",
            file_count=10,
        )
        session.add(project)
        session.flush()

        yield session, project.id


def test_save_skills_to_db_creates_skills_and_handles_duplicates(
    session_with_project: tuple[Session, int],
) -> None:
    """Test that save_skills_to_db creates Skill/ProjectSkill records and is idempotent."""
    session, project_id = session_with_project

    tools = {"Python", "Git"}
    practices = {"Unit Testing"}

    # First call creates skills and links
    save_skills_to_db(session, project_id, tools, practices)
    session.flush()

    all_skills = session.query(Skill).all()
    assert len(all_skills) == 3

    skill_map = {s.name: s.skill_type for s in all_skills}
    assert skill_map["Python"] == "tool"
    assert skill_map["Git"] == "tool"
    assert skill_map["Unit Testing"] == "practice"

    links = session.query(ProjectSkill).filter(ProjectSkill.project_id == project_id).all()
    assert len(links) == 3

    # Second call with overlapping skills doesn't create duplicates
    save_skills_to_db(session, project_id, {"Python", "Docker"}, {"Unit Testing", "CI/CD"})
    session.flush()

    # 5 unique skills total
    all_skills = session.query(Skill).all()
    assert len(all_skills) == 5
    assert {s.name for s in all_skills} == {"Python", "Git", "Docker", "Unit Testing", "CI/CD"}

    # 5 project-skill links (no duplicates)
    links = session.query(ProjectSkill).filter(ProjectSkill.project_id == project_id).all()
    assert len(links) == 5

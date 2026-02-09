from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from capstone_project_team_5.data import db as db_module
from capstone_project_team_5.data.db import Base
from capstone_project_team_5.data.models import Project, UploadRecord, User


@pytest.fixture(scope="function")
def tmp_db(monkeypatch, tmp_path):
    """Create a temporary database for testing."""

    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", TestingSessionLocal)

    yield

    engine.dispose()


@pytest.fixture
def seeded_user_project(tmp_db):
    """Create a user and project with no dates set."""

    with db_module.get_session() as session:
        # User
        user = User(username="testuser", password_hash="hash")
        session.add(user)
        session.flush()

        # UploadRecord
        upload = UploadRecord(
            filename="test.zip",
            size_bytes=1234,
            file_count=3,
        )
        session.add(upload)
        session.flush()

        # Project linked to upload (no dates)
        project = Project(
            upload_id=upload.id,
            name="Test Project",
            rel_path="test_project",
            has_git_repo=False,
            file_count=3,
            is_collaborative=False,
            start_date=None,
            end_date=None,
        )
        session.add(project)
        session.commit()

        return user.username, project.id


@pytest.fixture
def seeded_project_with_dates(tmp_db):
    """Create a project with dates already set."""

    with db_module.get_session() as session:
        upload = UploadRecord(
            filename="dated.zip",
            size_bytes=5678,
            file_count=10,
        )
        session.add(upload)
        session.flush()

        start = datetime(2024, 1, 1)
        end = datetime(2024, 6, 30)

        project = Project(
            upload_id=upload.id,
            name="Dated Project",
            rel_path="dated_project",
            has_git_repo=True,
            file_count=10,
            is_collaborative=False,
            start_date=start,
            end_date=end,
        )
        session.add(project)
        session.commit()

        return project.id, start, end


def test_project_dates_default_to_none(seeded_user_project):
    """Test that project dates default to None when not specified."""

    _username, project_id = seeded_user_project

    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        assert project is not None
        assert project.start_date is None
        assert project.end_date is None


def test_project_dates_can_be_set(seeded_user_project):
    """Test that project dates can be set and persisted."""

    _username, project_id = seeded_user_project

    start = datetime(2024, 1, 15)
    end = datetime(2024, 7, 20)

    # Set dates
    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        project.start_date = start
        project.end_date = end
        session.commit()

    # Verify persistence
    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        assert project.start_date == start
        assert project.end_date == end


def test_project_dates_are_date_objects(seeded_project_with_dates):
    """Test that dates are stored as date objects, not strings."""

    project_id, expected_start, expected_end = seeded_project_with_dates

    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        assert isinstance(project.start_date, datetime)
        assert isinstance(project.end_date, datetime)
        assert project.start_date == expected_start
        assert project.end_date == expected_end


def test_project_start_date_only(seeded_user_project):
    """Test that only start date can be set (end date remains None)."""

    username, project_id = seeded_user_project

    start = datetime(2024, 3, 1)

    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        project.start_date = start
        session.commit()

    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        assert project.start_date == start
        assert project.end_date is None


def test_project_end_date_only(seeded_user_project):
    """Test that only end date can be set (start date remains None)."""
    username, project_id = seeded_user_project

    end = datetime(2024, 12, 31)

    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        project.end_date = end
        session.commit()

    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        assert project.start_date is None
        assert project.end_date == end


def test_project_dates_can_be_updated(seeded_project_with_dates):
    """Test that existing dates can be updated to new values."""

    project_id, old_start, old_end = seeded_project_with_dates

    new_start = datetime(2024, 2, 1)
    new_end = datetime(2024, 8, 31)

    # Update dates
    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        project.start_date = new_start
        project.end_date = new_end
        session.commit()

    # Verify update
    with db_module.get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()

        assert project.start_date == new_start
        assert project.end_date == new_end
        assert project.start_date != old_start
        assert project.end_date != old_end

"""Tests for role detection database persistence."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, UploadRecord, User
from capstone_project_team_5.services.code_analysis_persistence import save_code_analysis_to_db
from capstone_project_team_5.services.project_analysis import ProjectAnalysis


@pytest.fixture
def temp_user() -> str:
    """Create a temporary user for testing."""
    username = f"test_user_{datetime.now().timestamp()}"
    with get_session() as session:
        user = User(username=username, password_hash="dummy_hash_for_testing")
        session.add(user)
        session.commit()
    return username


@pytest.fixture
def temp_project(temp_user: str) -> tuple[str, str]:
    """Create a temporary project in the database."""
    project_name = f"test_project_{datetime.now().timestamp()}"
    project_rel_path = f"path/to/{project_name}"

    with get_session() as session:
        upload = UploadRecord(
            filename="test.zip",
            size_bytes=1000,
            file_count=10,
        )
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name=project_name,
            rel_path=project_rel_path,
            has_git_repo=True,
            file_count=10,
            is_collaborative=False,
        )
        session.add(project)
        session.commit()

    return project_name, project_rel_path


def test_role_data_persisted_to_database(temp_user: str, temp_project: tuple[str, str]) -> None:
    """Test that role data is saved to the Project table."""
    project_name, project_rel_path = temp_project

    # Create analysis with role data
    analysis = ProjectAnalysis(
        project_path=Path("."),
        language="Python",
        user_role="Lead Developer",
        user_contribution_percentage=75.5,
    )

    # Save to database
    save_code_analysis_to_db(project_name, project_rel_path, analysis, username=temp_user)

    # Verify role data was saved
    with get_session() as session:
        project = (
            session.query(Project)
            .filter(Project.name == project_name, Project.rel_path == project_rel_path)
            .first()
        )

        assert project is not None
        assert project.user_role == "Lead Developer"
        assert project.user_contribution_percentage == 75.5


def test_role_data_none_when_not_provided(temp_user: str, temp_project: tuple[str, str]) -> None:
    """Test that role fields remain None when analysis doesn't include role data."""
    project_name, project_rel_path = temp_project

    # Create analysis without role data
    analysis = ProjectAnalysis(
        project_path=Path("."),
        language="Python",
        user_role=None,
        user_contribution_percentage=None,
    )

    # Save to database
    save_code_analysis_to_db(project_name, project_rel_path, analysis, username=temp_user)

    # Verify role data remains None
    with get_session() as session:
        project = (
            session.query(Project)
            .filter(Project.name == project_name, Project.rel_path == project_rel_path)
            .first()
        )

        assert project is not None
        assert project.user_role is None
        assert project.user_contribution_percentage is None


def test_role_data_updated_on_subsequent_save(
    temp_user: str, temp_project: tuple[str, str]
) -> None:
    """Test that role data is updated when analysis is run again."""
    project_name, project_rel_path = temp_project

    # First save with initial role data
    analysis1 = ProjectAnalysis(
        project_path=Path("."),
        language="Python",
        user_role="Contributor",
        user_contribution_percentage=25.0,
    )
    save_code_analysis_to_db(project_name, project_rel_path, analysis1, username=temp_user)

    # Second save with updated role data
    analysis2 = ProjectAnalysis(
        project_path=Path("."),
        language="Python",
        user_role="Lead Developer",
        user_contribution_percentage=85.0,
    )
    save_code_analysis_to_db(project_name, project_rel_path, analysis2, username=temp_user)

    # Verify role data was updated
    with get_session() as session:
        project = (
            session.query(Project)
            .filter(Project.name == project_name, Project.rel_path == project_rel_path)
            .first()
        )

        assert project is not None
        assert project.user_role == "Lead Developer"
        assert project.user_contribution_percentage == 85.0


def test_all_role_classifications_can_be_persisted(
    temp_user: str, temp_project: tuple[str, str]
) -> None:
    """Test that all role classifications can be saved and retrieved."""
    project_name, project_rel_path = temp_project

    roles = [
        ("Solo Developer", 100.0),
        ("Lead Developer", 75.0),
        ("Major Contributor", 45.0),
        ("Contributor", 20.0),
        ("Minor Contributor", 5.0),
    ]

    for role, percentage in roles:
        analysis = ProjectAnalysis(
            project_path=Path("."),
            language="Python",
            user_role=role,
            user_contribution_percentage=percentage,
        )
        save_code_analysis_to_db(project_name, project_rel_path, analysis, username=temp_user)

        with get_session() as session:
            project = (
                session.query(Project)
                .filter(Project.name == project_name, Project.rel_path == project_rel_path)
                .first()
            )

            assert project is not None
            assert project.user_role == role
            assert project.user_contribution_percentage == percentage


def test_role_justification_persisted_to_database(
    temp_user: str, temp_project: tuple[str, str]
) -> None:
    """Test that role justification is saved to the Project table."""
    project_name, project_rel_path = temp_project

    # Create analysis with role justification
    analysis = ProjectAnalysis(
        project_path=Path("."),
        language="Python",
        user_role="Lead Developer",
        user_contribution_percentage=75.5,
        role_justification="87 commits representing 75.5% of contributions with 2 other contributors",
    )

    # Save to database
    save_code_analysis_to_db(project_name, project_rel_path, analysis, username=temp_user)

    # Verify role justification was saved
    with get_session() as session:
        project = (
            session.query(Project)
            .filter(Project.name == project_name, Project.rel_path == project_rel_path)
            .first()
        )

        assert project is not None
        assert project.user_role == "Lead Developer"
        assert project.user_contribution_percentage == 75.5
        assert (
            project.role_justification
            == "87 commits representing 75.5% of contributions with 2 other contributors"
        )


def test_role_justification_none_when_not_provided(
    temp_user: str, temp_project: tuple[str, str]
) -> None:
    """Test that role_justification remains None when not included in analysis."""
    project_name, project_rel_path = temp_project

    # Create analysis without role justification
    analysis = ProjectAnalysis(
        project_path=Path("."),
        language="Python",
        user_role="Contributor",
        user_contribution_percentage=25.0,
        role_justification=None,
    )

    # Save to database
    save_code_analysis_to_db(project_name, project_rel_path, analysis, username=temp_user)

    # Verify role justification remains None
    with get_session() as session:
        project = (
            session.query(Project)
            .filter(Project.name == project_name, Project.rel_path == project_rel_path)
            .first()
        )

        assert project is not None
        assert project.role_justification is None

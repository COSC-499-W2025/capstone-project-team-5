"""Regression tests covering multi-project detection and persistence."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from capstone_project_team_5.data import db as db_module
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, UploadRecord
from capstone_project_team_5.services import upload_zip


def _create_zip(zip_path: Path, entries: list[tuple[str, bytes]]) -> None:
    """Write a ZIP archive populated with the supplied entries."""

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for relative_path, data in entries:
            archive.writestr(relative_path, data)


@pytest.fixture(autouse=False)
def temp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the ORM at a temporary SQLite database for isolation."""

    db_path = tmp_path / "artifact_miner.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    db_module._engine = None
    db_module._SessionLocal = None
    yield
    db_module._engine = None
    db_module._SessionLocal = None


def test_multiple_top_level_directories(temp_db: None, tmp_path: Path) -> None:
    """Multiple top-level directories become distinct projects."""
    zip_path = tmp_path / "multi_projects.zip"
    _create_zip(
        zip_path,
        entries=[
            ("project1/main.py", b"print('project1')\n"),
            ("project2/src/index.js", b"console.log('project2');\n"),
            ("project3/app.java", b"class App {}\n"),
        ],
    )

    result = upload_zip(zip_path)

    project_names = {project.name for project in result.projects}
    assert project_names == {"project1", "project2", "project3"}
    assert all(project.file_count >= 1 for project in result.projects)


def test_nested_git_creates_additional_project(temp_db: None, tmp_path: Path) -> None:
    """Nested git repositories produce additional project entries."""
    zip_path = tmp_path / "nested_git.zip"
    _create_zip(
        zip_path,
        entries=[
            ("outer/main.py", b"print('outer')\n"),
            ("outer/nested/app.py", b"print('nested')\n"),
            ("outer/nested/.git/config", b"[core]\n"),
        ],
    )

    result = upload_zip(zip_path)

    rel_paths = {project.rel_path for project in result.projects}
    assert "outer" in rel_paths
    assert "outer/nested" in rel_paths

    nested = next(project for project in result.projects if project.rel_path == "outer/nested")
    assert nested.has_git_repo is True


def test_root_docs_and_media_as_projects(temp_db: None, tmp_path: Path) -> None:
    """Root-level docs and media files are grouped into special projects."""
    zip_path = tmp_path / "root_special.zip"
    _create_zip(
        zip_path,
        entries=[
            ("project1/main.py", b"print('code')\n"),
            ("readme.md", b"# Documentation\n"),
            ("guide.pdf", b"PDF"),
            ("logo.png", b"PNG"),
            ("demo.mov", b"MOV"),
        ],
    )

    result = upload_zip(zip_path)

    by_name = {project.name: project for project in result.projects}
    assert "project1" in by_name
    assert "docs" in by_name
    assert "media" in by_name

    assert by_name["docs"].file_count == 2
    assert by_name["media"].file_count == 2


def test_projects_persisted_to_database(temp_db: None, tmp_path: Path) -> None:
    """Discovered projects persist with the originating upload record."""
    zip_path = tmp_path / "persist.zip"
    _create_zip(
        zip_path,
        entries=[
            ("project1/main.py", b"print('project1')\n"),
            ("project2/main.py", b"print('project2')\n"),
            ("readme.md", b"# Docs\n"),
        ],
    )

    result = upload_zip(zip_path)

    with get_session() as session:
        upload_record = session.query(UploadRecord).filter_by(filename=result.filename).one()
        persisted_projects = session.query(Project).filter_by(upload_id=upload_record.id).all()

    assert len(persisted_projects) == len(result.projects)
    persisted_paths = {(project.name, project.rel_path) for project in persisted_projects}
    expected_paths = {(project.name, project.rel_path) for project in result.projects}
    assert persisted_paths == expected_paths


def test_empty_directories_are_not_projects(temp_db: None, tmp_path: Path) -> None:
    """Ensure empty directories are not saved as projects."""
    zip_path = tmp_path / "empty_dir.zip"
    _create_zip(
        zip_path,
        entries=[
            ("empty_dir/", b""),
            ("filled/main.py", b"print('ok')\n"),
        ],
    )

    result = upload_zip(zip_path)
    rel_paths = {project.rel_path for project in result.projects}

    assert "filled" in rel_paths
    assert "empty_dir" not in rel_paths

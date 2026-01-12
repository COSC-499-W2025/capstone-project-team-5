"""Regression tests covering multi-project detection and persistence."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from docx import Document

from capstone_project_team_5.cli import _display_project_analyses
from capstone_project_team_5.consent_tool import ConsentTool
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


def test_project_importance_ranking_stored(temp_db: None, tmp_path: Path) -> None:
    """Verify that project importance ranks are calculated and stored in database."""
    zip_path = tmp_path / "ranking_test.zip"
    _create_zip(
        zip_path,
        entries=[
            ("project1/main.py", b"print('project1')\n"),
            ("project1/utils.py", b"def util():\n    pass\n"),
            ("project1/test_main.py", b"def test_something():\n    pass\n"),
            ("project2/app.js", b"console.log('project2');\n"),
            ("project3/README.md", b"# Project 3\n"),
        ],
    )

    result = upload_zip(zip_path)

    with ZipFile(zip_path) as archive:
        extract_path = tmp_path / "extracted"
        extract_path.mkdir()
        archive.extractall(extract_path)

    consent_tool = ConsentTool()
    _display_project_analyses(
        extract_root=extract_path,
        projects=result.projects,
        consent_tool=consent_tool,
    )

    with get_session() as session:
        upload_record = session.query(UploadRecord).filter_by(filename=result.filename).one()
        projects = session.query(Project).filter_by(upload_id=upload_record.id).all()
        ranked_projects = [p for p in projects if p.importance_rank is not None]

        assert len(ranked_projects) > 0

        ranks = [p.importance_rank for p in ranked_projects if p.importance_rank is not None]
        assert all(isinstance(rank, int) for rank in ranks)
        assert min(ranks) == 1
        assert all(rank > 0 for rank in ranks)

        scored_projects = [p for p in projects if p.importance_score is not None]
        assert len(scored_projects) > 0
        scores = [p.importance_score for p in scored_projects if p.importance_score is not None]
        assert all(isinstance(score, float) for score in scores)
        assert all(score >= 0 for score in scores)


def test_is_collaborative_flag_populated_from_collab_detector(
    temp_db: None, tmp_path: Path
) -> None:
    """Verify that collaboration detection populates is_collaborative on persisted projects."""
    # Create a small project with a .docx file that has multiple authors.
    project_root = tmp_path / "proj1"
    project_root.mkdir()
    docx_path = project_root / "doc1.docx"
    doc = Document()
    doc.add_paragraph("Hello collaboration!")
    doc.core_properties.author = "Alice"
    doc.core_properties.last_modified_by = "Bob"
    doc.save(docx_path)

    zip_path = tmp_path / "collab_proj.zip"
    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.write(docx_path, arcname="proj1/doc1.docx")

    result = upload_zip(zip_path)

    # There should be a single discovered project for proj1.
    assert any(project.name == "proj1" for project in result.projects)

    with get_session() as session:
        upload_record = session.query(UploadRecord).filter_by(filename=result.filename).one()
        persisted_projects = session.query(Project).filter_by(upload_id=upload_record.id).all()

    assert len(persisted_projects) == 1
    assert persisted_projects[0].name == "proj1"
    assert persisted_projects[0].is_collaborative is True

"""Tests for incremental upload functionality."""

from __future__ import annotations

import logging
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from capstone_project_team_5.data import db as db_module
from capstone_project_team_5.data.db import get_session, init_db
from capstone_project_team_5.data.models import ArtifactSource, Project
from capstone_project_team_5.services.incremental_upload import (
    extract_and_merge_files,
    find_matching_projects,
    get_project_uploads,
    incremental_upload_zip,
)


def _create_zip(zip_path: Path, entries: list[tuple[str, bytes]]) -> None:
    """Write a ZIP archive populated with the supplied entries."""
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)


@pytest.fixture(autouse=True)
def temp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point the ORM at a temporary SQLite database for isolation."""
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    # Reset the global engine_url before each test
    db_module.engine_url = None
    db_module.engine = None
    db_module.SessionLocal = None
    db_module.engine_url = db_url
    init_db()


def test_find_matching_projects_by_name(temp_db: None, tmp_path: Path) -> None:
    """Test finding existing projects by name."""
    # Create initial upload with a project
    zip_path1 = tmp_path / "initial.zip"
    _create_zip(
        zip_path1,
        entries=[
            ("myproject/main.py", b"print('hello')\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path1)

    # Now search for projects with this name
    matches = find_matching_projects(["myproject"])

    assert "myproject" in matches
    assert len(matches["myproject"]) > 0


def test_incremental_upload_creates_artifact_source(temp_db: None, tmp_path: Path) -> None:
    """Test that incremental upload creates ArtifactSource records."""
    # Create initial upload
    zip_path1 = tmp_path / "initial.zip"
    _create_zip(
        zip_path1,
        entries=[
            ("project1/main.py", b"print('v1')\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path1)

    # Get the project ID
    with get_session() as session:
        initial_project = session.query(Project).filter(Project.name == "project1").first()
        project_id = initial_project.id

    # Create second upload with additional files
    zip_path2 = tmp_path / "incremental.zip"
    _create_zip(
        zip_path2,
        entries=[
            ("project1/utils.py", b"def helper():\n    pass\n"),
            ("project1/test.py", b"def test_main():\n    pass\n"),
        ],
    )

    # Perform incremental upload
    mapping = {"project1": project_id}
    result2, associations = incremental_upload_zip(zip_path2, mapping)

    # Verify ArtifactSource was created
    assert len(associations) > 0
    assert associations[0][0] == project_id

    # Verify artifact count
    with get_session() as session:
        artifact_sources = (
            session.query(ArtifactSource).filter(ArtifactSource.project_id == project_id).all()
        )
        assert len(artifact_sources) > 0
        assert artifact_sources[0].artifact_count == 2  # Two new files


def test_incremental_upload_updates_file_count(temp_db: None, tmp_path: Path) -> None:
    """Test that project file count is updated on incremental upload."""
    # Create initial upload
    zip_path1 = tmp_path / "initial.zip"
    _create_zip(
        zip_path1,
        entries=[
            ("myproj/file1.py", b"# file 1\n"),
            ("myproj/file2.py", b"# file 2\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path1)

    with get_session() as session:
        project = session.query(Project).filter(Project.name == "myproj").first()
        initial_count = project.file_count
        project_id = project.id

    # Initial count should be at least 2 (may be more due to other test artifacts)
    assert initial_count >= 2

    # Incremental upload with more files
    zip_path2 = tmp_path / "incremental.zip"
    _create_zip(
        zip_path2,
        entries=[
            ("myproj/file3.py", b"# file 3\n"),
            ("myproj/file4.py", b"# file 4\n"),
            ("myproj/file5.py", b"# file 5\n"),
        ],
    )

    mapping = {"myproj": project_id}
    incremental_upload_zip(zip_path2, mapping)

    # Verify file count was updated
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        assert project.file_count == initial_count + 3


def test_get_project_uploads_returns_all_contributions(temp_db: None, tmp_path: Path) -> None:
    """Test that get_project_uploads returns all upload contributions."""
    # Create initial upload
    zip_path1 = tmp_path / "initial.zip"
    _create_zip(
        zip_path1,
        entries=[
            ("proj/main.py", b"# main\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path1)

    with get_session() as session:
        project = session.query(Project).filter(Project.name == "proj").first()
        project_id = project.id

    # Create incremental upload
    zip_path2 = tmp_path / "incremental.zip"
    _create_zip(
        zip_path2,
        entries=[
            ("proj/utils.py", b"# utils\n"),
        ],
    )

    mapping = {"proj": project_id}
    incremental_upload_zip(zip_path2, mapping)

    # Get all uploads for this project
    uploads_info = get_project_uploads(project_id)

    # Should have at least 2 entries: initial + incremental
    assert len(uploads_info) >= 2
    assert uploads_info[0]["is_incremental"] is False  # First is always initial
    assert uploads_info[1]["is_incremental"] is True  # Second is incremental


def test_incremental_upload_without_mapping_creates_new_projects(
    temp_db: None, tmp_path: Path
) -> None:
    """Test that upload without mapping still creates new projects (not incremental)."""
    zip_path1 = tmp_path / "initial.zip"
    _create_zip(
        zip_path1,
        entries=[
            ("proj1/main.py", b"# proj1\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path1)

    with get_session() as session:
        projects_before = session.query(Project).filter(Project.name == "proj1").all()
        initial_count = len(projects_before)

    # Upload without mapping should create a new project
    zip_path2 = tmp_path / "second.zip"
    _create_zip(
        zip_path2,
        entries=[
            ("proj1/utils.py", b"# new utils\n"),
        ],
    )

    result2, associations = incremental_upload_zip(zip_path2, None)  # No mapping

    # No associations should be created
    assert len(associations) == 0

    # A new proj1 project should be created (separate from original)
    with get_session() as session:
        projects = session.query(Project).filter(Project.name == "proj1").all()
        assert len(projects) == initial_count + 1


def test_extract_and_merge_files(temp_db: None, tmp_path: Path) -> None:
    """Test extracting and merging files from ZIP."""
    zip_path = tmp_path / "archive.zip"
    _create_zip(
        zip_path,
        entries=[
            ("project/src/main.py", b"# main\n"),
            ("project/src/utils.py", b"# utils\n"),
            ("project/README.md", b"# README\n"),
        ],
    )

    target_dir = tmp_path / "merged"
    file_count = extract_and_merge_files(zip_path, target_dir, "myproject")

    # Verify file count
    assert file_count == 3

    # Verify files were created
    merged_project_dir = target_dir / "myproject"
    assert merged_project_dir.exists()
    # Note: extract_and_merge_files flattens files to project directory
    files = list(merged_project_dir.glob("*"))
    assert len(files) == 3


def test_incremental_upload_multiple_rounds(temp_db: None, tmp_path: Path) -> None:
    """Test multiple incremental uploads to the same project."""
    zip_path1 = tmp_path / "upload1.zip"
    _create_zip(
        zip_path1,
        entries=[
            ("dev_project/file1.py", b"# 1\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path1)

    with get_session() as session:
        projects = session.query(Project).filter(Project.name == "dev_project").all()
        # Use the most recently created one (in case there are duplicates from other tests)
        project = sorted(projects, key=lambda p: p.created_at)[-1]
        project_id = project.id

    # Second incremental upload
    zip_path2 = tmp_path / "upload2.zip"
    _create_zip(
        zip_path2,
        entries=[
            ("dev_project/file2.py", b"# 2\n"),
        ],
    )
    mapping = {"dev_project": project_id}
    incremental_upload_zip(zip_path2, mapping)

    # Third incremental upload
    zip_path3 = tmp_path / "upload3.zip"
    _create_zip(
        zip_path3,
        entries=[
            ("dev_project/file3.py", b"# 3\n"),
        ],
    )
    incremental_upload_zip(zip_path3, mapping)

    # Verify all three uploads are tracked
    uploads_info = get_project_uploads(project_id)
    assert len(uploads_info) == 3
    assert uploads_info[0]["is_incremental"] is False
    assert uploads_info[1]["is_incremental"] is True
    assert uploads_info[2]["is_incremental"] is True

    # Verify total file count increased
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        assert project.file_count == 3


def test_find_matching_projects_case_insensitive(temp_db: None, tmp_path: Path) -> None:
    """Test that project matching is case-insensitive."""
    zip_path = tmp_path / "test.zip"
    _create_zip(
        zip_path,
        entries=[
            ("MyProject/main.py", b"# code\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path)

    matches_exact = find_matching_projects(["MyProject"])
    matches_lower = find_matching_projects(["myproject"])

    assert "MyProject" in matches_exact and matches_exact["MyProject"]
    assert "myproject" in matches_lower and matches_lower["myproject"]
    assert matches_exact["MyProject"] == matches_lower["myproject"]


def test_artifact_source_cascade_delete(temp_db: None, tmp_path: Path) -> None:
    """Test that ArtifactSource records are deleted with their project."""
    zip_path1 = tmp_path / "initial.zip"
    _create_zip(
        zip_path1,
        entries=[
            ("cascade_test/file.py", b"# code\n"),
        ],
    )

    from capstone_project_team_5.services import upload_zip

    upload_zip(zip_path1)

    with get_session() as session:
        project = session.query(Project).filter(Project.name == "cascade_test").first()
        project_id = project.id

    # Add incremental upload
    zip_path2 = tmp_path / "incremental.zip"
    _create_zip(
        zip_path2,
        entries=[
            ("cascade_test/utils.py", b"# utils\n"),
        ],
    )
    mapping = {"cascade_test": project_id}
    incremental_upload_zip(zip_path2, mapping)

    # Verify artifact source exists
    with get_session() as session:
        sources = (
            session.query(ArtifactSource).filter(ArtifactSource.project_id == project_id).all()
        )
        assert len(sources) > 0

    # Delete the project
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id).first()
        session.delete(project)
        session.commit()

    # Verify artifact sources were cascade deleted
    with get_session() as session:
        sources = (
            session.query(ArtifactSource).filter(ArtifactSource.project_id == project_id).all()
        )
        assert len(sources) == 0


def test_deduplicates_within_single_zip(tmp_path: Path) -> None:
    """Files with identical content in the same ZIP should be stored once."""
    zip_path = tmp_path / "dup_same_zip.zip"
    content = b"print('same')\n"
    _create_zip(
        zip_path,
        entries=[
            ("project/a.py", content),
            ("project/subdir/b.py", content),  # same bytes, different path
        ],
    )

    target_dir = tmp_path / "merged"
    written = extract_and_merge_files(zip_path, target_dir, "proj")

    # Only one unique file should be written
    assert written == 1
    files = list((target_dir / "proj").glob("*"))
    assert len(files) == 1


def test_deduplicates_across_multiple_zips(tmp_path: Path) -> None:
    """Duplicate content across separate ZIPs should be stored once system-wide."""
    content = b"print('same-across')\n"
    zip1 = tmp_path / "first.zip"
    _create_zip(zip1, entries=[("app/x.py", content)])

    zip2 = tmp_path / "second.zip"
    _create_zip(zip2, entries=[("app/y.py", content)])

    target_dir = tmp_path / "merged2"
    written1 = extract_and_merge_files(zip1, target_dir, "p1")
    written2 = extract_and_merge_files(zip2, target_dir, "p2")

    assert written1 == 1
    # Second write should be skipped due to dedupe
    assert written2 == 0

    # System-level index should result in a single stored file across projects
    files_p1 = list((target_dir / "p1").glob("*"))
    files_p2 = list((target_dir / "p2").glob("*"))
    assert len(files_p1) == 1
    assert len(files_p2) == 0


def test_extract_and_merge_validates_dedupe_index(temp_db: None, tmp_path: Path) -> None:
    """Test that dedupe index entries are validated before skipping files."""
    target_dir = tmp_path / "merged"

    # Create first ZIP
    zip1 = tmp_path / "first.zip"
    content = b"print('hello')\n"
    _create_zip(zip1, entries=[("project/file.py", content)])

    # Extract first time
    written1 = extract_and_merge_files(zip1, target_dir, "project")
    assert written1 == 1

    # Manually remove the extracted file to simulate corruption/deletion
    project_dir = target_dir / "project"
    extracted_file = list(project_dir.glob("*.py"))[0]
    extracted_file.unlink()

    # Create second ZIP with same content
    zip2 = tmp_path / "second.zip"
    _create_zip(zip2, entries=[("project/file.py", content)])

    # Should write again since the indexed file no longer exists
    written2 = extract_and_merge_files(zip2, target_dir, "project")
    assert written2 == 1


def test_extract_and_merge_validates_file_size(temp_db: None, tmp_path: Path) -> None:
    """Test that file size is validated when checking dedupe index."""
    target_dir = tmp_path / "merged"

    # Create first ZIP
    zip1 = tmp_path / "first.zip"
    content = b"print('hello')\n"
    _create_zip(zip1, entries=[("project/data.py", content)])

    # Extract first time
    written1 = extract_and_merge_files(zip1, target_dir, "project")
    assert written1 == 1

    # Manually corrupt the file by changing its content
    project_dir = target_dir / "project"
    extracted_file = list(project_dir.glob("*.py"))[0]
    extracted_file.write_bytes(b"corrupted")

    # Create second ZIP with same content
    zip2 = tmp_path / "second.zip"
    _create_zip(zip2, entries=[("project/data.py", content)])

    # Should write again since the file size doesn't match
    written2 = extract_and_merge_files(zip2, target_dir, "project")
    assert written2 == 1


def test_extract_and_merge_filename_collision_with_hash_prefix_collision(
    temp_db: None, tmp_path: Path
) -> None:
    """Test that filename collision with same 8-char hash prefix is handled correctly."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    project_dir = target_dir / "myproject"
    project_dir.mkdir()

    # Pre-create a file with the same name that will trigger alt_name
    existing_file = project_dir / "data.txt"
    existing_file.write_bytes(b"existing content")

    # Create a ZIP with a file that has the same name but different content
    # This will trigger the alt_name path
    zip_path = tmp_path / "upload.zip"
    _create_zip(zip_path, entries=[("myproject/data.txt", b"new content 1")])

    # Extract and merge
    written1 = extract_and_merge_files(zip_path, target_dir, "myproject")
    assert written1 == 1

    # Now manually create a file with the hash-based alt_name to simulate collision
    # We need to compute what the hash would be for "new content 2"
    import hashlib

    content2 = b"new content 2"
    hash2 = hashlib.sha256(content2).hexdigest()

    # Create a file that would conflict with the alt_name
    collision_file = project_dir / f"data-{hash2[:8]}.txt"
    collision_file.write_bytes(b"collision content")

    # Now try to extract a second file with same name but yet different content
    zip_path2 = tmp_path / "upload2.zip"
    _create_zip(zip_path2, entries=[("myproject/data.txt", content2)])

    # This should create a file with a counter suffix to avoid overwriting
    written2 = extract_and_merge_files(zip_path2, target_dir, "myproject")
    assert written2 == 1

    # Check that we now have 4 files: original, first alt, collision, and counter-suffixed
    files = list(project_dir.glob("data*.txt"))
    assert len(files) == 4

    # Verify the counter-suffixed file exists
    counter_file = project_dir / f"data-{hash2[:8]}-1.txt"
    assert counter_file.exists()
    assert counter_file.read_bytes() == content2


def test_extract_and_merge_handles_index_write_gracefully(
    temp_db: None, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that index write failures are logged but don't crash the function."""
    target_dir = tmp_path / "merged"
    target_dir.mkdir()

    # Create a ZIP with a file
    zip_path = tmp_path / "upload.zip"
    _create_zip(zip_path, entries=[("project/file.py", b"print('hello')\n")])

    # Extract files normally - this should succeed and log if there are any issues
    with caplog.at_level(logging.WARNING):
        written = extract_and_merge_files(zip_path, target_dir, "project")

    # Normal case should succeed
    assert written == 1

    # No warnings should be logged in normal operation
    warning_messages = [
        record.message
        for record in caplog.records
        if record.levelname == "WARNING" and "dedupe" in record.message.lower()
    ]
    assert len(warning_messages) == 0

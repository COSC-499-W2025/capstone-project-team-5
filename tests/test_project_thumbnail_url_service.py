from __future__ import annotations

from pathlib import Path

import pytest

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.db import get_session, init_db
from capstone_project_team_5.data.models import Project, UploadRecord, User
from capstone_project_team_5.services.project_thumbnail import (
    MAX_THUMBNAIL_BYTES,
    clear_project_thumbnail,
    get_project_thumbnail_path,
    has_project_thumbnail,
    set_project_thumbnail,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake"
JPEG_BYTES = b"\xff\xd8\xff" + b"fake"


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary database and reset global engine/session."""
    db_path = tmp_path / "thumb.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("ZIP2JOB_UPLOAD_DIR", str(tmp_path / "uploads"))
    db_module._engine = None
    db_module._SessionLocal = None

    init_db()
    yield db_path

    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = None
    db_module._SessionLocal = None


def _create_user_and_project() -> int:
    with get_session() as session:
        user = User(username="thumb_user", password_hash="hash")
        session.add(user)
        session.flush()

        upload = UploadRecord(filename="sample.zip", size_bytes=100, file_count=1)
        session.add(upload)
        session.flush()

        project = Project(
            upload_id=upload.id,
            name="Thumb Project",
            rel_path="proj",
            has_git_repo=False,
            file_count=1,
            is_collaborative=False,
        )
        session.add(project)
        session.flush()

        return project.id


def test_set_and_get_thumbnail(temp_db: Path) -> None:
    project_id = _create_user_and_project()

    saved, error = set_project_thumbnail(
        project_id, filename="thumb.png", content_type="image/png", data=PNG_BYTES
    )
    assert saved is True
    assert error is None
    path = get_project_thumbnail_path(project_id)
    assert path is not None
    assert path.exists()
    assert has_project_thumbnail(project_id) is True


def test_overwrite_thumbnail(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    assert set_project_thumbnail(
        project_id, filename="thumb.png", content_type="image/png", data=PNG_BYTES
    )[0]
    assert set_project_thumbnail(
        project_id, filename="thumb.jpg", content_type="image/jpeg", data=JPEG_BYTES
    )[0]
    path = get_project_thumbnail_path(project_id)
    assert path is not None
    assert path.suffix == ".jpg"
    assert path.with_suffix(".png").exists() is False


def test_clear_thumbnail(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    assert set_project_thumbnail(
        project_id, filename="thumb.png", content_type="image/png", data=PNG_BYTES
    )[0]
    assert clear_project_thumbnail(project_id) is True
    assert has_project_thumbnail(project_id) is False
    assert clear_project_thumbnail(project_id) is False


def test_reject_invalid_thumbnail(temp_db: Path) -> None:
    project_id = _create_user_and_project()

    saved, error = set_project_thumbnail(
        project_id, filename="thumb.png", content_type="image/png", data=b"not-an-image"
    )
    assert saved is False
    assert error
    assert has_project_thumbnail(project_id) is False


def test_reject_mismatched_content_type(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    saved, error = set_project_thumbnail(
        project_id, filename="thumb.png", content_type="image/jpeg", data=PNG_BYTES
    )
    assert saved is False
    assert error


def test_reject_too_large_thumbnail(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    data = b"\x89PNG\r\n\x1a\n" + (b"a" * (MAX_THUMBNAIL_BYTES + 1))
    saved, error = set_project_thumbnail(
        project_id, filename="thumb.png", content_type="image/png", data=data
    )
    assert saved is False
    assert error

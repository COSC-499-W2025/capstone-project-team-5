import os
import tempfile
from pathlib import Path

import pytest

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.db import get_session, init_db
from capstone_project_team_5.data.models import Project, UploadRecord, User
from capstone_project_team_5.services.project_thumbnail import (
    clear_project_thumbnail_url,
    get_project_thumbnail_url,
    set_project_thumbnail_url,
)


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary database and reset global engine/session."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    original_db_url = os.environ.get("DB_URL")
    os.environ["DB_URL"] = f"sqlite:///{db_path}"
    db_module._engine = None
    db_module._SessionLocal = None

    init_db()
    yield db_path

    os.environ.pop("DB_URL", None)
    if original_db_url:
        os.environ["DB_URL"] = original_db_url
    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = None
    db_module._SessionLocal = None
    db_path.unlink(missing_ok=True)


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


def test_set_and_get_thumbnail_url(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    url = "https://example.com/thumb.png"

    saved = set_project_thumbnail_url(project_id, url)
    assert saved is True

    assert get_project_thumbnail_url(project_id) == url


def test_update_thumbnail_url(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    first = "https://example.com/first.png"
    second = "https://example.com/second.png"

    assert set_project_thumbnail_url(project_id, first) is True
    assert set_project_thumbnail_url(project_id, second) is True
    assert get_project_thumbnail_url(project_id) == second


def test_clear_thumbnail_url(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    url = "https://example.com/thumb.png"

    assert set_project_thumbnail_url(project_id, url) is True
    assert clear_project_thumbnail_url(project_id) is True
    assert get_project_thumbnail_url(project_id) is None
    assert clear_project_thumbnail_url(project_id) is False


def test_reject_invalid_thumbnail_url(temp_db: Path) -> None:
    project_id = _create_user_and_project()

    assert set_project_thumbnail_url(project_id, "not-a-url") is False
    assert set_project_thumbnail_url(project_id, "ftp://example.com/thumb.png") is False
    assert set_project_thumbnail_url(project_id, "https://example.com") is False
    assert set_project_thumbnail_url(project_id, "https://example.com/thumb.txt") is False
    assert set_project_thumbnail_url(project_id, "") is False
    assert get_project_thumbnail_url(project_id) is None


def test_accept_thumbnail_url_with_query(temp_db: Path) -> None:
    project_id = _create_user_and_project()
    url = "https://cdn.example.com/thumb.png?size=200"

    assert set_project_thumbnail_url(project_id, url) is True
    assert get_project_thumbnail_url(project_id) == url

"""Tests for portfolio item creation and update services."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from capstone_project_team_5.data import db as db_module
from capstone_project_team_5.data.db import get_session, init_db
from capstone_project_team_5.data.models import PortfolioItem, Project, UploadRecord, User
from capstone_project_team_5.services.portfolio_persistence import (
    create_portfolio_item,
    get_latest_portfolio_item_for_project,
    update_portfolio_item,
)


@pytest.fixture
def temp_db() -> Iterator[Path]:
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


def _create_upload() -> int:
    """Helper to create an upload record and return its ID."""
    with get_session() as session:
        upload = UploadRecord(filename="test.zip", size_bytes=1234, file_count=10)
        session.add(upload)
        session.flush()
        return upload.id


def _create_project() -> int:
    """Helper to create a project and return its ID."""
    upload_id = _create_upload()
    with get_session() as session:
        project = Project(
            upload_id=upload_id,
            name="Showcase Project",
            rel_path="/demo/project",
            has_git_repo=False,
            file_count=5,
            is_collaborative=False,
        )
        session.add(project)
        session.flush()
        return project.id


def _create_user(username: str = "testuser") -> str:
    """Helper to create a user and return their username."""
    with get_session() as session:
        user = User(username=username, password_hash="fakehash123")
        session.add(user)
        session.flush()
        return user.username


def test_create_portfolio_item_with_project(temp_db: Path) -> None:
    """Create a portfolio item linked to a specific project."""
    username = _create_user()
    project_id = _create_project()

    content = {
        "summary": "A demo showcase project.",
        "bullets": ["Implemented feature X", "Optimized Y"],
        "links": ["https://example.com/demo"],
    }

    item = create_portfolio_item(
        username=username,
        project_id=project_id,
        title="Demo Showcase",
        content=content,
    )

    assert item.id is not None
    assert item.project_id == project_id
    assert item.title == "Demo Showcase"

    # Verify content persisted as JSON string and is decodable.
    with get_session() as session:
        from_db = session.query(PortfolioItem).filter(PortfolioItem.id == item.id).first()
        assert from_db is not None
        decoded = json.loads(from_db.content)
        assert decoded["summary"] == "A demo showcase project."
        assert decoded["bullets"][0].startswith("Implemented")


def test_create_portfolio_item_without_project(temp_db: Path) -> None:
    """Create a standalone portfolio item with no associated project."""
    username = _create_user()
    content = {"summary": "Standalone portfolio entry", "bullets": ["Independent work"]}

    item = create_portfolio_item(
        username=username,
        project_id=None,
        title="Independent Showcase",
        content=content,
    )

    assert item.id is not None
    assert item.project_id is None
    assert item.title == "Independent Showcase"


def test_update_portfolio_item_changes_title_and_content(temp_db: Path) -> None:
    """Update both title and content for an existing portfolio item."""
    username = _create_user()
    project_id = _create_project()
    original_content = {"summary": "Original", "bullets": ["Old bullet"]}

    item = create_portfolio_item(
        username=username,
        project_id=project_id,
        title="Original Title",
        content=original_content,
    )

    updated_content = {"summary": "Updated summary", "bullets": ["New bullet"], "tags": ["python"]}
    updated = update_portfolio_item(
        item_id=item.id,
        title="Updated Title",
        content=updated_content,
    )

    assert updated is not None
    assert updated.id == item.id
    assert updated.title == "Updated Title"

    decoded = json.loads(updated.content)
    assert decoded["summary"] == "Updated summary"
    assert decoded["tags"] == ["python"]


def test_update_portfolio_item_partial_update(temp_db: Path) -> None:
    """Update only the title, preserving existing content."""
    username = _create_user()
    project_id = _create_project()
    original_content = {"summary": "keep me", "bullets": ["keep this bullet"]}

    item = create_portfolio_item(
        username=username,
        project_id=project_id,
        title="Initial Title",
        content=original_content,
    )

    updated = update_portfolio_item(item_id=item.id, title="Renamed Title")

    assert updated is not None
    assert updated.title == "Renamed Title"

    decoded = json.loads(updated.content)
    assert decoded["summary"] == "keep me"


def test_update_portfolio_item_nonexistent_returns_none(temp_db: Path) -> None:
    """Updating a non-existent portfolio item should return None."""
    result = update_portfolio_item(item_id=99999, title="Does not exist")
    assert result is None


def test_get_latest_portfolio_item_for_project(temp_db: Path) -> None:
    """Return the most recently created portfolio item for a project."""
    username = _create_user()
    project_id = _create_project()

    create_portfolio_item(
        username=username,
        project_id=project_id,
        title="First",
        content={"markdown": "first"},
    )
    second = create_portfolio_item(
        username=username,
        project_id=project_id,
        title="Second",
        content={"markdown": "second"},
    )

    latest = get_latest_portfolio_item_for_project(project_id)
    assert latest is not None
    assert latest.id == second.id


def test_get_latest_portfolio_item_for_project_no_items(temp_db: Path) -> None:
    """Return None when no portfolio items exist for a project."""
    project_id = _create_project()
    latest = get_latest_portfolio_item_for_project(project_id)
    assert latest is None

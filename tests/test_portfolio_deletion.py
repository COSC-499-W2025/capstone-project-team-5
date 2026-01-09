"""Unit tests for portfolio item deletion service.

Tests cover deleting portfolio items (generated insights/reports) while
ensuring that underlying project data and shared artifacts remain intact.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from capstone_project_team_5.data import db as db_module
from capstone_project_team_5.data.db import get_session, init_db
from capstone_project_team_5.data.models import PortfolioItem, Project, UploadRecord, User
from capstone_project_team_5.services.portfolio_deletion import (
    clear_all_portfolio_items,
    delete_portfolio_item,
    delete_portfolio_items_by_project,
)


@pytest.fixture
def temp_db() -> Iterator[Path]:
    """Create a temporary database with ORM models."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Set up the database URL to use the temp file
    original_db_url = os.environ.get("DB_URL")
    os.environ["DB_URL"] = f"sqlite:///{db_path}"

    # Reset the engine and session factory
    db_module._engine = None
    db_module._SessionLocal = None

    # Initialize the database (creates tables)
    init_db()

    yield db_path

    # Cleanup
    os.environ.pop("DB_URL", None)
    if original_db_url:
        os.environ["DB_URL"] = original_db_url

    # Properly dispose of the engine to release file locks (important for Windows)
    if db_module._engine is not None:
        db_module._engine.dispose()

    # Reset the engine and session factory
    db_module._engine = None
    db_module._SessionLocal = None

    db_path.unlink(missing_ok=True)


def _create_user(username: str = "testuser") -> int:
    """Helper to create a user and return their ID."""
    with get_session() as session:
        user = User(username=username, password_hash="fakehash123")
        session.add(user)
        session.flush()
        user_id = user.id
        return user_id


def _create_upload(name: str = "test.zip") -> int:
    """Helper to create an upload record and return its ID."""
    with get_session() as session:
        upload = UploadRecord(
            filename=name,
            size_bytes=1024,
            file_count=10,
        )
        session.add(upload)
        session.flush()
        upload_id = upload.id
        return upload_id


def _create_project(upload_id: int | None = None, name: str = "Test Project") -> int:
    """Helper to create a project and return its ID."""
    if upload_id is None:
        upload_id = _create_upload()

    with get_session() as session:
        project = Project(
            upload_id=upload_id,
            name=name,
            rel_path="/test/project",
            has_git_repo=False,
            file_count=5,
            is_collaborative=False,
        )
        session.add(project)
        session.flush()
        project_id = project.id
        return project_id


def _create_portfolio_item(
    project_id: int | None = None,
    user_id: int | None = None,
    title: str = "Test Item",
    content: str = "# Test Portfolio Item\n\nThis is test content.",
) -> int:
    """Helper to create a portfolio item and return its ID."""
    if user_id is None:
        user_id = _create_user()

    with get_session() as session:
        item = PortfolioItem(
            project_id=project_id,
            user_id=user_id,
            title=title,
            content=content,
        )
        session.add(item)
        session.flush()
        item_id = item.id
        return item_id


def _count_portfolio_items(project_id: int | None = None, user_id: int | None = None) -> int:
    """Helper to count portfolio items."""
    with get_session() as session:
        query = session.query(PortfolioItem)
        if project_id is not None:
            query = query.filter(PortfolioItem.project_id == project_id)
        if user_id is not None:
            query = query.filter(PortfolioItem.user_id == user_id)
        return query.count()


def _count_projects() -> int:
    """Helper to count projects."""
    with get_session() as session:
        return session.query(Project).count()


def _portfolio_item_exists(item_id: int) -> bool:
    """Helper to check if a portfolio item exists."""
    with get_session() as session:
        item = session.query(PortfolioItem).filter(PortfolioItem.id == item_id).first()
        return item is not None


def test_delete_portfolio_item_existing_record(temp_db: Path) -> None:
    """Test deleting an existing portfolio item returns True."""
    user_id = _create_user()
    project_id = _create_project()
    item_id = _create_portfolio_item(project_id, user_id)

    deleted = delete_portfolio_item(item_id)
    assert deleted is True
    assert not _portfolio_item_exists(item_id)


def test_delete_portfolio_item_non_existent_record(temp_db: Path) -> None:
    """Test deleting a non-existent portfolio item returns False."""
    deleted = delete_portfolio_item(999)
    assert deleted is False


def test_delete_portfolio_item_preserves_project(temp_db: Path) -> None:
    """Test that deleting a portfolio item doesn't delete the project."""
    user_id = _create_user()
    project_id = _create_project(name="Important Project")
    item_id = _create_portfolio_item(project_id, user_id)

    assert _count_projects() == 1

    delete_portfolio_item(item_id)

    # Project should still exist
    assert _count_projects() == 1


def test_delete_portfolio_items_by_project_removes_all_matching(temp_db: Path) -> None:
    """Test deleting all portfolio items for a specific project."""
    user_id = _create_user()
    project1_id = _create_project(name="Project 1")
    project2_id = _create_project(name="Project 2")

    # Create multiple items for project 1
    _create_portfolio_item(project1_id, user_id, "Item 1")
    _create_portfolio_item(project1_id, user_id, "Item 2")
    _create_portfolio_item(project1_id, user_id, "Item 3")

    # Create item for project 2
    _create_portfolio_item(project2_id, user_id, "Item 4")

    count = delete_portfolio_items_by_project(project1_id)
    assert count == 3

    # Verify project 1 items are gone
    assert _count_portfolio_items(project1_id) == 0

    # Verify project 2 item remains
    assert _count_portfolio_items(project2_id) == 1


def test_delete_portfolio_items_by_project_no_matches(temp_db: Path) -> None:
    """Test deleting portfolio items for a project with no items returns 0."""
    project_id = _create_project()

    count = delete_portfolio_items_by_project(project_id)
    assert count == 0


def test_delete_portfolio_items_by_project_preserves_project(temp_db: Path) -> None:
    """Test that deleting portfolio items doesn't delete the project."""
    user_id = _create_user()
    project_id = _create_project(name="Project")
    _create_portfolio_item(project_id, user_id)
    _create_portfolio_item(project_id, user_id)

    assert _count_projects() == 1

    delete_portfolio_items_by_project(project_id)

    # Project should still exist
    assert _count_projects() == 1


def test_delete_portfolio_items_shared_project(temp_db: Path) -> None:
    """Test that deleting items from one project doesn't affect items from other projects."""
    user_id = _create_user()
    shared_project_id = _create_project(name="Shared Project")

    # Create items for the shared project
    item1 = _create_portfolio_item(shared_project_id, user_id, "Report 1")
    item2 = _create_portfolio_item(shared_project_id, user_id, "Report 2")

    # Create another project with items
    other_project_id = _create_project(name="Other Project")
    other_item = _create_portfolio_item(other_project_id, user_id, "Other Report")

    # Delete items from shared project
    count = delete_portfolio_items_by_project(shared_project_id)
    assert count == 2

    # Verify items are deleted
    assert not _portfolio_item_exists(item1)
    assert not _portfolio_item_exists(item2)

    # Verify other project's item remains
    assert _portfolio_item_exists(other_item)

    # Verify both projects still exist
    assert _count_projects() == 2


def test_clear_all_portfolio_items_removes_everything(temp_db: Path) -> None:
    """Test clearing all portfolio items removes all items."""
    user_id = _create_user()
    project1_id = _create_project(name="Project 1")
    project2_id = _create_project(name="Project 2")

    _create_portfolio_item(project1_id, user_id, "Item 1")
    _create_portfolio_item(project1_id, user_id, "Item 2")
    _create_portfolio_item(project2_id, user_id, "Item 3")

    assert _count_portfolio_items() == 3

    count = clear_all_portfolio_items()
    assert count == 3

    # Verify all items are gone
    assert _count_portfolio_items() == 0


def test_clear_all_portfolio_items_empty_database(temp_db: Path) -> None:
    """Test clearing portfolio items when database is already empty."""
    count = clear_all_portfolio_items()
    assert count == 0


def test_clear_all_portfolio_items_preserves_projects(temp_db: Path) -> None:
    """Test that clearing all portfolio items doesn't delete projects."""
    user_id = _create_user()
    project1_id = _create_project(name="Project 1")
    project2_id = _create_project(name="Project 2")

    _create_portfolio_item(project1_id, user_id)
    _create_portfolio_item(project2_id, user_id)

    assert _count_projects() == 2

    clear_all_portfolio_items()

    # Projects should still exist
    assert _count_projects() == 2


def test_delete_multiple_items_sequentially(temp_db: Path) -> None:
    """Test deleting multiple portfolio items one by one."""
    user_id = _create_user()
    project_id = _create_project()
    item1 = _create_portfolio_item(project_id, user_id, "Item 1")
    item2 = _create_portfolio_item(project_id, user_id, "Item 2")
    item3 = _create_portfolio_item(project_id, user_id, "Item 3")

    assert _count_portfolio_items() == 3

    assert delete_portfolio_item(item1) is True
    assert _count_portfolio_items() == 2

    assert delete_portfolio_item(item2) is True
    assert _count_portfolio_items() == 1

    assert delete_portfolio_item(item3) is True
    assert _count_portfolio_items() == 0


def test_delete_same_item_twice(temp_db: Path) -> None:
    """Test attempting to delete the same portfolio item twice."""
    user_id = _create_user()
    project_id = _create_project()
    item_id = _create_portfolio_item(project_id, user_id)

    assert delete_portfolio_item(item_id) is True
    assert delete_portfolio_item(item_id) is False


def test_portfolio_items_with_null_project_id(temp_db: Path) -> None:
    """Test deleting portfolio items that have NULL project_id."""
    user_id = _create_user()
    # Create item without project association (project_id is nullable in schema)
    item_id = _create_portfolio_item(project_id=None, user_id=user_id, title="Orphan Item")

    assert _count_portfolio_items() == 1

    deleted = delete_portfolio_item(item_id)
    assert deleted is True
    assert _count_portfolio_items() == 0


def test_multiple_users_same_project(temp_db: Path) -> None:
    """Test that multiple users can have portfolio items for the same project."""
    user1_id = _create_user("user1")
    user2_id = _create_user("user2")
    project_id = _create_project()

    # Each user creates their own portfolio item for the same project
    item1 = _create_portfolio_item(
        project_id, user1_id, "User 1's Portfolio", "User 1's custom content"
    )
    item2 = _create_portfolio_item(
        project_id, user2_id, "User 2's Portfolio", "User 2's custom content"
    )

    assert _count_portfolio_items(project_id) == 2

    # Delete user1's item
    delete_portfolio_item(item1)

    # User2's item should remain
    assert _portfolio_item_exists(item2)
    assert _count_portfolio_items(project_id) == 1


def test_user_specific_deletion(temp_db: Path) -> None:
    """Test deleting portfolio items for a specific user."""
    user1_id = _create_user("user1")
    user2_id = _create_user("user2")
    project_id = _create_project()

    # Create items for both users
    _create_portfolio_item(project_id, user1_id, "User 1 Item 1")
    _create_portfolio_item(project_id, user1_id, "User 1 Item 2")
    _create_portfolio_item(project_id, user2_id, "User 2 Item")

    assert _count_portfolio_items(user_id=user1_id) == 2
    assert _count_portfolio_items(user_id=user2_id) == 1

    # Delete all of user1's items
    with get_session() as session:
        deleted_count = (
            session.query(PortfolioItem).filter(PortfolioItem.user_id == user1_id).delete()
        )
        session.commit()

    assert deleted_count == 2
    assert _count_portfolio_items(user_id=user1_id) == 0
    assert _count_portfolio_items(user_id=user2_id) == 1


def test_large_batch_deletion(temp_db: Path) -> None:
    """Test deleting a large number of portfolio items."""
    user_id = _create_user()
    project_id = _create_project()

    # Create 100 portfolio items
    for i in range(100):
        _create_portfolio_item(project_id, user_id, f"Item {i}", f"Content for item {i}")

    assert _count_portfolio_items(project_id) == 100

    # Delete all at once
    count = delete_portfolio_items_by_project(project_id)
    assert count == 100
    assert _count_portfolio_items(project_id) == 0

    # Project should still exist
    assert _count_projects() == 1


def test_cascade_delete_on_user_deletion(temp_db: Path) -> None:
    """Test that portfolio items are deleted when user is deleted (CASCADE)."""
    user_id = _create_user("testuser")
    project_id = _create_project()

    _create_portfolio_item(project_id, user_id, "Item 1")
    _create_portfolio_item(project_id, user_id, "Item 2")

    assert _count_portfolio_items(user_id=user_id) == 2

    # Delete the user
    with get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        session.delete(user)
        session.commit()

    # Portfolio items should be automatically deleted due to CASCADE
    assert _count_portfolio_items(user_id=user_id) == 0

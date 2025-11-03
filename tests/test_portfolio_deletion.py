"""Unit tests for portfolio item deletion service.

Tests cover deleting portfolio items (generated insights/reports) while
ensuring that underlying project data and shared artifacts remain intact.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from capstone_project_team_5.services.portfolio_deletion import (
    clear_all_portfolio_items,
    delete_portfolio_item,
    delete_portfolio_items_by_project,
)


@pytest.fixture
def temp_db() -> Iterator[Path]:
    """Create a temporary database with the artifact_miner schema."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create schema
    cur.execute(
        """
        CREATE TABLE Project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            is_collaborative BOOLEAN NOT NULL DEFAULT 0,
            start_date DATE,
            end_date DATE,
            language TEXT,
            framework TEXT,
            importance_rank INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE Artifact (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            path TEXT NOT NULL,
            type TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE PortfolioItem (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE SET NULL
        )
        """
    )

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    db_path.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def mock_db_path(temp_db: Path, monkeypatch) -> None:
    """Mock the database path to use the temporary database."""
    from capstone_project_team_5.services import portfolio_deletion

    monkeypatch.setattr(portfolio_deletion, "_get_db_path", lambda: temp_db)


def _create_project(db_path: Path, name: str = "Test Project") -> int:
    """Helper to create a project and return its ID."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Project (name, description, language) VALUES (?, ?, ?)",
        (name, "Test description", "Python"),
    )
    project_id = cur.lastrowid
    conn.commit()
    conn.close()
    return project_id


def _create_artifact(db_path: Path, project_id: int, path: str = "/test/file.py") -> int:
    """Helper to create an artifact and return its ID."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Artifact (project_id, path, type) VALUES (?, ?, ?)",
        (project_id, path, "code"),
    )
    artifact_id = cur.lastrowid
    conn.commit()
    conn.close()
    return artifact_id


def _create_portfolio_item(
    db_path: Path,
    project_id: int | None = None,
    title: str = "Test Item",
    content: dict | None = None,
) -> int:
    """Helper to create a portfolio item and return its ID."""
    if content is None:
        content = {"bullets": ["Developed feature X", "Implemented Y"]}

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO PortfolioItem (project_id, title, content) VALUES (?, ?, ?)",
        (project_id, title, json.dumps(content)),
    )
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return item_id


def _count_portfolio_items(db_path: Path, project_id: int | None = None) -> int:
    """Helper to count portfolio items."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if project_id is not None:
        cur.execute("SELECT COUNT(*) FROM PortfolioItem WHERE project_id = ?", (project_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM PortfolioItem")
    count = cur.fetchone()[0]
    conn.close()
    return count


def _count_projects(db_path: Path) -> int:
    """Helper to count projects."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Project")
    count = cur.fetchone()[0]
    conn.close()
    return count


def _count_artifacts(db_path: Path) -> int:
    """Helper to count artifacts."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Artifact")
    count = cur.fetchone()[0]
    conn.close()
    return count


def _portfolio_item_exists(db_path: Path, item_id: int) -> bool:
    """Helper to check if a portfolio item exists."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM PortfolioItem WHERE id = ?", (item_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def test_delete_portfolio_item_existing_record(temp_db: Path) -> None:
    """Test deleting an existing portfolio item returns True."""
    project_id = _create_project(temp_db)
    item_id = _create_portfolio_item(temp_db, project_id)

    deleted = delete_portfolio_item(item_id)
    assert deleted is True
    assert not _portfolio_item_exists(temp_db, item_id)


def test_delete_portfolio_item_non_existent_record(temp_db: Path) -> None:
    """Test deleting a non-existent portfolio item returns False."""
    deleted = delete_portfolio_item(999)
    assert deleted is False


def test_delete_portfolio_item_preserves_project(temp_db: Path) -> None:
    """Test that deleting a portfolio item doesn't delete the project."""
    project_id = _create_project(temp_db, "Important Project")
    item_id = _create_portfolio_item(temp_db, project_id)

    assert _count_projects(temp_db) == 1

    delete_portfolio_item(item_id)

    # Project should still exist
    assert _count_projects(temp_db) == 1


def test_delete_portfolio_item_preserves_artifacts(temp_db: Path) -> None:
    """Test that deleting a portfolio item doesn't delete artifacts."""
    project_id = _create_project(temp_db)
    _create_artifact(temp_db, project_id, "/src/main.py")
    _create_artifact(temp_db, project_id, "/src/utils.py")
    item_id = _create_portfolio_item(temp_db, project_id)

    assert _count_artifacts(temp_db) == 2

    delete_portfolio_item(item_id)

    # Artifacts should still exist
    assert _count_artifacts(temp_db) == 2


def test_delete_portfolio_items_by_project_removes_all_matching(temp_db: Path) -> None:
    """Test deleting all portfolio items for a specific project."""
    project1_id = _create_project(temp_db, "Project 1")
    project2_id = _create_project(temp_db, "Project 2")

    # Create multiple items for project 1
    _create_portfolio_item(temp_db, project1_id, "Item 1")
    _create_portfolio_item(temp_db, project1_id, "Item 2")
    _create_portfolio_item(temp_db, project1_id, "Item 3")

    # Create item for project 2
    _create_portfolio_item(temp_db, project2_id, "Item 4")

    count = delete_portfolio_items_by_project(project1_id)
    assert count == 3

    # Verify project 1 items are gone
    assert _count_portfolio_items(temp_db, project1_id) == 0

    # Verify project 2 item remains
    assert _count_portfolio_items(temp_db, project2_id) == 1


def test_delete_portfolio_items_by_project_no_matches(temp_db: Path) -> None:
    """Test deleting portfolio items for a project with no items returns 0."""
    project_id = _create_project(temp_db)

    count = delete_portfolio_items_by_project(project_id)
    assert count == 0


def test_delete_portfolio_items_by_project_preserves_project(temp_db: Path) -> None:
    """Test that deleting portfolio items doesn't delete the project."""
    project_id = _create_project(temp_db, "Project")
    _create_portfolio_item(temp_db, project_id)
    _create_portfolio_item(temp_db, project_id)

    assert _count_projects(temp_db) == 1

    delete_portfolio_items_by_project(project_id)

    # Project should still exist
    assert _count_projects(temp_db) == 1


def test_delete_portfolio_items_shared_project(temp_db: Path) -> None:
    """Test that deleting items from one project doesn't affect items from other projects."""
    shared_project_id = _create_project(temp_db, "Shared Project")

    # Create items for the shared project
    item1 = _create_portfolio_item(temp_db, shared_project_id, "Report 1")
    item2 = _create_portfolio_item(temp_db, shared_project_id, "Report 2")

    # Create another project with items
    other_project_id = _create_project(temp_db, "Other Project")
    other_item = _create_portfolio_item(temp_db, other_project_id, "Other Report")

    # Delete items from shared project
    count = delete_portfolio_items_by_project(shared_project_id)
    assert count == 2

    # Verify items are deleted
    assert not _portfolio_item_exists(temp_db, item1)
    assert not _portfolio_item_exists(temp_db, item2)

    # Verify other project's item remains
    assert _portfolio_item_exists(temp_db, other_item)

    # Verify both projects still exist
    assert _count_projects(temp_db) == 2


def test_clear_all_portfolio_items_removes_everything(temp_db: Path) -> None:
    """Test clearing all portfolio items removes all items."""
    project1_id = _create_project(temp_db, "Project 1")
    project2_id = _create_project(temp_db, "Project 2")

    _create_portfolio_item(temp_db, project1_id, "Item 1")
    _create_portfolio_item(temp_db, project1_id, "Item 2")
    _create_portfolio_item(temp_db, project2_id, "Item 3")

    assert _count_portfolio_items(temp_db) == 3

    count = clear_all_portfolio_items()
    assert count == 3

    # Verify all items are gone
    assert _count_portfolio_items(temp_db) == 0


def test_clear_all_portfolio_items_empty_database(temp_db: Path) -> None:
    """Test clearing portfolio items when database is already empty."""
    count = clear_all_portfolio_items()
    assert count == 0


def test_clear_all_portfolio_items_preserves_projects(temp_db: Path) -> None:
    """Test that clearing all portfolio items doesn't delete projects."""
    project1_id = _create_project(temp_db, "Project 1")
    project2_id = _create_project(temp_db, "Project 2")

    _create_portfolio_item(temp_db, project1_id)
    _create_portfolio_item(temp_db, project2_id)

    assert _count_projects(temp_db) == 2

    clear_all_portfolio_items()

    # Projects should still exist
    assert _count_projects(temp_db) == 2


def test_clear_all_portfolio_items_preserves_artifacts(temp_db: Path) -> None:
    """Test that clearing all portfolio items doesn't delete artifacts."""
    project_id = _create_project(temp_db)
    _create_artifact(temp_db, project_id, "/src/file1.py")
    _create_artifact(temp_db, project_id, "/src/file2.py")
    _create_portfolio_item(temp_db, project_id)

    assert _count_artifacts(temp_db) == 2

    clear_all_portfolio_items()

    # Artifacts should still exist
    assert _count_artifacts(temp_db) == 2


def test_delete_multiple_items_sequentially(temp_db: Path) -> None:
    """Test deleting multiple portfolio items one by one."""
    project_id = _create_project(temp_db)
    item1 = _create_portfolio_item(temp_db, project_id, "Item 1")
    item2 = _create_portfolio_item(temp_db, project_id, "Item 2")
    item3 = _create_portfolio_item(temp_db, project_id, "Item 3")

    assert _count_portfolio_items(temp_db) == 3

    assert delete_portfolio_item(item1) is True
    assert _count_portfolio_items(temp_db) == 2

    assert delete_portfolio_item(item2) is True
    assert _count_portfolio_items(temp_db) == 1

    assert delete_portfolio_item(item3) is True
    assert _count_portfolio_items(temp_db) == 0


def test_delete_same_item_twice(temp_db: Path) -> None:
    """Test attempting to delete the same portfolio item twice."""
    project_id = _create_project(temp_db)
    item_id = _create_portfolio_item(temp_db, project_id)

    assert delete_portfolio_item(item_id) is True
    assert delete_portfolio_item(item_id) is False


def test_portfolio_items_with_null_project_id(temp_db: Path) -> None:
    """Test deleting portfolio items that have NULL project_id."""
    # Create item without project association
    item_id = _create_portfolio_item(temp_db, project_id=None, title="Orphan Item")

    assert _count_portfolio_items(temp_db) == 1

    deleted = delete_portfolio_item(item_id)
    assert deleted is True
    assert _count_portfolio_items(temp_db) == 0


def test_complex_json_content_preservation(temp_db: Path) -> None:
    """Test that complex JSON content is properly handled during deletion."""
    project_id = _create_project(temp_db)
    complex_content = {
        "bullets": ["Point 1", "Point 2"],
        "skills": ["Python", "SQL"],
        "metadata": {"version": "1.0", "tags": ["backend", "database"]},
    }
    item_id = _create_portfolio_item(temp_db, project_id, content=complex_content)

    # Verify item was created properly
    assert _portfolio_item_exists(temp_db, item_id)

    # Delete it
    delete_portfolio_item(item_id)

    # Verify it's gone
    assert not _portfolio_item_exists(temp_db, item_id)


def test_large_batch_deletion(temp_db: Path) -> None:
    """Test deleting a large number of portfolio items."""
    project_id = _create_project(temp_db)

    # Create 100 portfolio items
    for i in range(100):
        _create_portfolio_item(temp_db, project_id, f"Item {i}")

    assert _count_portfolio_items(temp_db, project_id) == 100

    # Delete all at once
    count = delete_portfolio_items_by_project(project_id)
    assert count == 100
    assert _count_portfolio_items(temp_db, project_id) == 0

    # Project should still exist
    assert _count_projects(temp_db) == 1

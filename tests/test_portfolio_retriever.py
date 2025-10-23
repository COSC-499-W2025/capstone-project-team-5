import json
import sqlite3
from pathlib import Path

import pytest

import outputs.portfolio_retriever as pr


@pytest.fixture
def temp_db(tmp_path: Path):
    """
    Create a temporary SQLite database with Project and PortfolioItem tables.

    Yields a Path to the DB file so tests can monkeypatch the module's DB_PATH.
    """
    db_path = tmp_path / "test_portfolio.db"
    conn = sqlite3.connect(db_path)
    # Ensure foreign key behavior for any FK semantics
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    cur.executescript(
        """
    CREATE TABLE Project (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE PortfolioItem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE SET NULL
    );
    """
    )

    # Insert a project
    cur.execute(
        "INSERT INTO Project (name, description) VALUES (?, ?)",
        ("Artifact Miner", "Test project for portfolio retriever"),
    )
    pid = cur.lastrowid

    # Insert two portfolio items with JSON content and different created_at timestamps
    items = [
        (pid, "First Item", json.dumps({"summary": "first", "score": 1}), "2024-10-01T12:00:00"),
        (pid, "Second Item", json.dumps({"summary": "second", "score": 2}), "2024-10-02T12:00:00"),
    ]
    cur.executemany(
        "INSERT INTO PortfolioItem (project_id, title, content, created_at) VALUES (?,?,?,?)",
        items,
    )

    conn.commit()
    conn.close()
    yield db_path


def test_get_existing_and_list_all(monkeypatch, temp_db: Path):
    """
    The retriever should return deserialized content and list items in
    reverse chronological order.
    """
    # Ensure the module points at our temporary DB file (Path-like)
    monkeypatch.setattr(pr, "DB_PATH", temp_db)

    # Get first item (id=1)
    item1 = pr.get(1)
    assert item1 is not None
    assert item1["id"] == 1
    assert item1["title"] == "First Item"
    assert item1["content"] == {"summary": "first", "score": 1}

    # list_all should return items ordered by created_at DESC, so id=2 first
    items = pr.list_all()
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0]["id"] == 2
    assert items[1]["id"] == 1


def test_get_nonexistent_returns_none(monkeypatch, temp_db: Path):
    monkeypatch.setattr(pr, "DB_PATH", temp_db)
    assert pr.get(9999) is None


def test_list_limit(monkeypatch, temp_db: Path):
    monkeypatch.setattr(pr, "DB_PATH", temp_db)
    items = pr.list_all(limit=1)
    assert len(items) == 1


def test_missing_database_raises(monkeypatch, tmp_path: Path):
    """
    If the DB file does not exist, _get_conn should raise
    FileNotFoundError via the public API.
    """
    non_existent = tmp_path / "nope.db"
    monkeypatch.setattr(pr, "DB_PATH", non_existent)
    with pytest.raises(FileNotFoundError):
        pr.get(1)

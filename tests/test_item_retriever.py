import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from outputs.item_retriever import ItemRetriever


@pytest.fixture
def temp_db(tmp_path: Path):
    """Create a temporary SQLite database using SQLAlchemy and populate it.

    Yields a SQLAlchemy-compatible SQLite URL (string) pointing to the
    created database so tests can configure the module via the
    `DATABASE_URL` environment variable.
    """
    db_path = tmp_path / "test_generated.db"
    sqlite_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(sqlite_url)

    ddl = """
    CREATE TABLE Project (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE GeneratedItem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        kind TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE SET NULL
    );
    """

    # Use SQLAlchemy connection/transaction to create tables and insert data
    with engine.begin() as conn:
        # SQLite DBAPI doesn't allow executing multiple statements at once
        for stmt in (s.strip() for s in ddl.split(";") if s.strip()):
            conn.execute(text(stmt))
        conn.execute(
            text("INSERT INTO Project (name, description) VALUES (:name, :desc)"),
            {"name": "Artifact Miner", "desc": "Test project for item retriever"},
        )
        # Insert two generated items of kind 'portfolio'
        conn.execute(
            text(
                "INSERT INTO GeneratedItem (project_id, kind, title, content, created_at) "
                "VALUES (:pid, :kind, :title, :content, :created_at)"
            ),
            {
                "pid": 1,
                "kind": "portfolio",
                "title": "First Item",
                "content": json.dumps({"summary": "first", "score": 1}),
                "created_at": "2024-10-01T12:00:00",
            },
        )
        conn.execute(
            text(
                "INSERT INTO GeneratedItem (project_id, kind, title, content, created_at) "
                "VALUES (:pid, :kind, :title, :content, :created_at)"
            ),
            {
                "pid": 1,
                "kind": "portfolio",
                "title": "Second Item",
                "content": json.dumps({"summary": "second", "score": 2}),
                "created_at": "2024-10-02T12:00:00",
            },
        )

        # Insert two generated items of kind 'resume'
        conn.execute(
            text(
                "INSERT INTO GeneratedItem (project_id, kind, title, content, created_at) "
                "VALUES (:pid, :kind, :title, :content, :created_at)"
            ),
            {
                "pid": 1,
                "kind": "resume",
                "title": "Resume Item One",
                "content": json.dumps({"name": "Alice", "experience": 5}),
                "created_at": "2024-11-01T09:00:00",
            },
        )
        conn.execute(
            text(
                "INSERT INTO GeneratedItem (project_id, kind, title, content, created_at) "
                "VALUES (:pid, :kind, :title, :content, :created_at)"
            ),
            {
                "pid": 1,
                "kind": "resume",
                "title": "Resume Item Two",
                "content": json.dumps({"name": "Bob", "experience": 7}),
                "created_at": "2024-11-02T09:00:00",
            },
        )

    yield sqlite_url


def test_get_existing_and_list_all(monkeypatch, temp_db: str):
    """The retriever should return deserialized content and list items in
    reverse chronological order when filtered by kind.
    """
    # Configure the ItemRetriever to use our temporary DB via DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", temp_db)

    retriever = ItemRetriever("GeneratedItem", kind="portfolio")

    # Get first item (id=1)
    item1 = retriever.get(1)
    assert item1 is not None
    assert item1["id"] == 1
    assert item1["title"] == "First Item"
    assert item1["content"] == {"summary": "first", "score": 1}

    # list_all should return items ordered by created_at DESC, so id=2 first
    items = retriever.list_all()
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0]["id"] == 2
    assert items[1]["id"] == 1


def test_get_nonexistent_returns_none(monkeypatch, temp_db: str):
    monkeypatch.setenv("DATABASE_URL", temp_db)
    retriever = ItemRetriever("GeneratedItem", kind="portfolio")
    assert retriever.get(9999) is None


def test_list_limit(monkeypatch, temp_db: str):
    monkeypatch.setenv("DATABASE_URL", temp_db)
    retriever = ItemRetriever("GeneratedItem", kind="portfolio")
    items = retriever.list_all(limit=1)
    assert len(items) == 1


def test_get_existing_and_list_all_resume(monkeypatch, temp_db: str):
    """Mirror of the portfolio test for items with kind='resume'."""
    monkeypatch.setenv("DATABASE_URL", temp_db)

    retriever = ItemRetriever("GeneratedItem", kind="resume")

    # The resume items were inserted after the portfolio items and should have
    # ids 3 and 4; the later created_at (id=4) should appear first.
    item = retriever.get(3)
    assert item is not None
    assert item["id"] == 3
    assert item["title"] == "Resume Item One"
    assert item["content"] == {"name": "Alice", "experience": 5}

    items = retriever.list_all()
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0]["id"] == 4
    assert items[1]["id"] == 3


def test_list_limit_resume(monkeypatch, temp_db: str):
    monkeypatch.setenv("DATABASE_URL", temp_db)
    retriever = ItemRetriever("GeneratedItem", kind="resume")
    items = retriever.list_all(limit=1)
    assert len(items) == 1


def test_missing_database_raises(monkeypatch, tmp_path: Path):
    """If the DB file is missing, connecting will fail (no tables)."""
    non_existent = tmp_path / "nope.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{non_existent.as_posix()}")
    retriever = ItemRetriever("GeneratedItem", kind="portfolio")
    with pytest.raises(OperationalError):
        retriever.get(1)

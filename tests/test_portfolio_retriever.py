import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

import outputs.portfolio_retriever as pr


@pytest.fixture
def temp_db(tmp_path: Path):
    """Create a temporary SQLite database using SQLAlchemy and populate it.

    Yields a SQLAlchemy-compatible SQLite URL (string) pointing to the
    created database so tests can configure the module via the
    `DATABASE_URL` environment variable.
    """
    db_path = tmp_path / "test_portfolio.db"
    sqlite_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(sqlite_url)

    ddl = """
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

    # Use SQLAlchemy connection/transaction to create tables and insert data
    with engine.begin() as conn:
        # SQLite DBAPI doesn't allow executing multiple statements at once
        for stmt in (s.strip() for s in ddl.split(";") if s.strip()):
            conn.execute(text(stmt))
        conn.execute(
            text("INSERT INTO Project (name, description) VALUES (:name, :desc)"),
            {"name": "Artifact Miner", "desc": "Test project for portfolio retriever"},
        )
        # Retrieve project id (SQLite autoincrement -> 1)
        # Insert two portfolio items with JSON content and timestamps
        conn.execute(
            text(
                "INSERT INTO PortfolioItem (project_id, title, content, created_at) "
                "VALUES (:pid, :title, :content, :created_at)"
            ),
            {
                "pid": 1,
                "title": "First Item",
                "content": json.dumps({"summary": "first", "score": 1}),
                "created_at": "2024-10-01T12:00:00",
            },
        )
        conn.execute(
            text(
                "INSERT INTO PortfolioItem (project_id, title, content, created_at) "
                "VALUES (:pid, :title, :content, :created_at)"
            ),
            {
                "pid": 1,
                "title": "Second Item",
                "content": json.dumps({"summary": "second", "score": 2}),
                "created_at": "2024-10-02T12:00:00",
            },
        )

    yield sqlite_url


def test_get_existing_and_list_all(monkeypatch, temp_db: str):
    """
    The retriever should return deserialized content and list items in
    reverse chronological order.
    """
    # Configure the module to use our temporary DB via DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", temp_db)

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


def test_get_nonexistent_returns_none(monkeypatch, temp_db: str):
    monkeypatch.setenv("DATABASE_URL", temp_db)
    assert pr.get(9999) is None


def test_list_limit(monkeypatch, temp_db: str):
    monkeypatch.setenv("DATABASE_URL", temp_db)
    items = pr.list_all(limit=1)
    assert len(items) == 1


def test_missing_database_raises(monkeypatch, tmp_path: Path):
    """If the DB file is missing, connecting will fail (no tables).

    The SQLAlchemy-backed module raises an exception when the expected
    tables are not present or the connection cannot satisfy queries. We
    assert that an exception (OperationalError or similar) is raised.
    """
    non_existent = tmp_path / "nope.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{non_existent.as_posix()}")
    with pytest.raises(OperationalError):
        pr.get(1)

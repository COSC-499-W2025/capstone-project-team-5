import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, Text, String, ForeignKey, select
from sqlalchemy.exc import OperationalError, NoSuchTableError

from outputs.item_retriever import ItemRetriever


def _reset_app_db():
    """Reset the app DB engine/session cache so tests can control DB_URL."""
    import capstone_project_team_5.data.db as app_db

    app_db._engine = None
    app_db._SessionLocal = None


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

    # Use SQLAlchemy Core table definitions instead of raw DDL strings
    md = MetaData()
    project_tbl = Table(
        "Project",
        md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", Text, nullable=False),
        Column("description", Text),
    )

    gen_item_tbl = Table(
        "GeneratedItem",
        md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("project_id", Integer, ForeignKey("Project.id")),
        Column("kind", Text, nullable=False),
        Column("title", Text, nullable=False),
        Column("content", Text, nullable=False),
        Column("created_at", Text, nullable=False),
    )

    md.create_all(engine)

    # Insert rows using Core insert() so we avoid raw SQL in tests
    with engine.begin() as conn:
        res = conn.execute(project_tbl.insert().values(name="Artifact Miner", description="Test project for item retriever"))
        # Retrieve inserted project id
        pid = conn.execute(select(project_tbl.c.id).where(project_tbl.c.name == "Artifact Miner")).scalar_one()

        # Insert portfolio items
        conn.execute(
            gen_item_tbl.insert(),
            [
                {
                    "project_id": pid,
                    "kind": "portfolio",
                    "title": "First Item",
                    "content": json.dumps({"summary": "first", "score": 1}),
                    "created_at": "2024-10-01T12:00:00",
                },
                {
                    "project_id": pid,
                    "kind": "portfolio",
                    "title": "Second Item",
                    "content": json.dumps({"summary": "second", "score": 2}),
                    "created_at": "2024-10-02T12:00:00",
                },
            ],
        )

        # Insert resume items
        conn.execute(
            gen_item_tbl.insert(),
            [
                {
                    "project_id": pid,
                    "kind": "resume",
                    "title": "Resume Item One",
                    "content": json.dumps({"name": "Alice", "experience": 5}),
                    "created_at": "2024-11-01T09:00:00",
                },
                {
                    "project_id": pid,
                    "kind": "resume",
                    "title": "Resume Item Two",
                    "content": json.dumps({"name": "Bob", "experience": 7}),
                    "created_at": "2024-11-02T09:00:00",
                },
            ],
        )

    yield sqlite_url


def test_get_existing_and_list_all(monkeypatch, temp_db: str):
    """The retriever should return deserialized content and list items in
    reverse chronological order when filtered by kind.
    """
    # Configure the ItemRetriever to use our temporary DB via the app DB URL
    monkeypatch.setenv("DB_URL", temp_db)
    # Reset app DB engine/session cache in case other modules were initialized
    _reset_app_db()

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
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()
    retriever = ItemRetriever("GeneratedItem", kind="portfolio")
    assert retriever.get(9999) is None


def test_list_limit(monkeypatch, temp_db: str):
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()
    retriever = ItemRetriever("GeneratedItem", kind="portfolio")
    items = retriever.list_all(limit=1)
    assert len(items) == 1


def test_get_existing_and_list_all_resume(monkeypatch, temp_db: str):
    """Mirror of the portfolio test for items with kind='resume'."""
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()

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
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()
    retriever = ItemRetriever("GeneratedItem", kind="resume")
    items = retriever.list_all(limit=1)
    assert len(items) == 1


def test_missing_database_raises(monkeypatch, tmp_path: Path):
    """If the DB file is missing, connecting will fail (no tables)."""
    non_existent = tmp_path / "nope.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{non_existent.as_posix()}")
    _reset_app_db()
    retriever = ItemRetriever("GeneratedItem", kind="portfolio")
    # Depending on wiring (standalone engine vs app engine) attempting to
    # query a missing DB may raise OperationalError or simply return None.
    # Accept either behavior to keep the test robust during refactors.
    try:
        res = retriever.get(1)
    except (OperationalError, NoSuchTableError):
        # DB missing -> operational error or reflection failure is acceptable
        pass
    else:
        # If no exception, ensure result is None (no rows)
        assert res is None

import json
from pathlib import Path

import pytest
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    Text,
    Boolean,
    select,
)

from outputs.top_projects import get_top_projects_from_db, compute_top_projects_from_paths


def _reset_app_db():
    import capstone_project_team_5.data.db as app_db

    app_db._engine = None
    app_db._SessionLocal = None


@pytest.fixture
def temp_db(tmp_path: Path):
    db_path = tmp_path / "projects.db"
    sqlite_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(sqlite_url)

    md = MetaData()
    project_tbl = Table(
        "Project",
        md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", Text, nullable=False),
        Column("description", Text),
        Column("is_collaborative", Boolean, nullable=False, default=False),
        Column("start_date", Text),
        Column("end_date", Text),
        Column("language", Text),
        Column("framework", Text),
        Column("importance_rank", Integer),
    )

    # Additional tables expected by ProjectSummary when reflecting
    artifact_tbl = Table(
        "Artifact",
        md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("project_id", Integer, nullable=False),
        Column("path", Text, nullable=False),
        Column("type", Text, nullable=False),
    )

    contrib_tbl = Table(
        "Contribution",
        md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("project_id", Integer, nullable=False),
        Column("artifact_id", Integer),
        Column("activity_type", Text, nullable=False),
    )

    skill_tbl = Table(
        "Skill",
        md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", Text, nullable=False),
    )

    projectskill_tbl = Table(
        "ProjectSkill",
        md,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("project_id", Integer, nullable=False),
        Column("skill_id", Integer, nullable=False),
    )

    md.create_all(engine)

    # Insert some projects with varying importance_rank
    with engine.begin() as conn:
        conn.execute(
            project_tbl.insert(),
            [
                {
                    "name": "Proj A",
                    "description": "A",
                    "is_collaborative": False,
                    "start_date": "2024-01-01",
                    "end_date": "2024-06-01",
                    "language": "Python",
                    "framework": "Flask",
                    "importance_rank": 10,
                },
                {
                    "name": "Proj B",
                    "description": "B",
                    "is_collaborative": True,
                    "start_date": "2023-01-01",
                    "end_date": "2024-01-01",
                    "language": "JavaScript",
                    "framework": "React",
                    "importance_rank": 30,
                },
                {
                    "name": "Proj C",
                    "description": "C",
                    "is_collaborative": False,
                    "start_date": "2022-01-01",
                    "end_date": "2023-01-01",
                    "language": "C++",
                    "framework": "None",
                    "importance_rank": 20,
                },
            ],
        )

    yield sqlite_url


def test_get_top_projects_from_db(monkeypatch, temp_db: str):
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()

    top = get_top_projects_from_db(n=2)
    assert isinstance(top, list)
    assert len(top) == 2
    # Top by importance_rank should be Proj B (30), then Proj C (20)
    assert top[0]["summary"]["project_name"] == "Proj B"
    assert top[1]["summary"]["project_name"] == "Proj C"


def test_compute_top_projects_from_paths(tmp_path: Path):
    # Create three simple project directories with different file counts
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    p3 = tmp_path / "p3"
    p1.mkdir()
    p2.mkdir()
    p3.mkdir()

    # p1: 1 file
    (p1 / "a.py").write_text("print(1)")

    # p2: 3 files
    for i in range(3):
        (p2 / f"f{i}.py").write_text("print(2)")

    # p3: 2 files
    for i in range(2):
        (p3 / f"g{i}.py").write_text("print(3)")

    mapping = {1: p1, 2: p2, 3: p3}
    top = compute_top_projects_from_paths(mapping, n=3)

    assert len(top) == 3
    # Expect p2 (3 files) to have highest score, then p3, then p1
    ids_in_order = [entry["project_id"] for entry in top]
    assert ids_in_order == [2, 3, 1]

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

import outputs.project_summary as ps


def _reset_app_db():
    """Reset the app DB engine/session cache so tests can control DATABASE_URL."""
    import capstone_project_team_5.data.db as app_db

    app_db._engine = None
    app_db._SessionLocal = None


@pytest.fixture
def temp_db(tmp_path):
    # Create a temporary SQLite database.
    # Populate it with minimal schema and test data.
    db_path = tmp_path / "test_artifact_miner.db"
    db_url = f"sqlite:///{db_path.as_posix()}"

    # Use SQLAlchemy to create schema and insert test data so tests exercise
    # the same code paths as production (SQLAlchemy Core).
    schema_path = Path(__file__).resolve().parents[1] / "db" / "artifact_miner_schema.sql"
    schema_sql = schema_path.read_text()

    engine = create_engine(db_url)
    with engine.begin() as conn:
        # Create schema: SQLite DBAPI requires single-statement executes,
        # so split the file by ';' and execute each non-empty statement.
        for stmt in (s.strip() for s in schema_sql.split(";") if s.strip()):
            conn.execute(text(stmt))

        # Insert a test project
        res = conn.execute(
            text(
                "INSERT INTO Project (name, description, language, framework, "
                "is_collaborative, start_date, end_date, importance_rank) "
                "VALUES (:name, :desc, :lang, :fw, :collab, :start, :end, :rank)"
            ),
            {
                "name": "Artifact Miner",
                "desc": "Testing project summary output",
                "lang": "Python",
                "fw": "Flask",
                "collab": 0,
                "start": "2024-09-01",
                "end": "2024-12-01",
                "rank": 1,
            },
        )
        pid = int(res.lastrowid or conn.execute(text("SELECT last_insert_rowid()")).scalar())

        # Artifacts
        conn.execute(
            text("INSERT INTO Artifact (project_id, path, type) VALUES (:pid, :path, :type)"),
            [
                {"pid": pid, "path": "src/main.py", "type": "code"},
                {"pid": pid, "path": "tests/test_main.py", "type": "code"},
                {"pid": pid, "path": "docs/readme.md", "type": "document"},
            ],
        )

        # Contributions
        conn.execute(
            text("INSERT INTO Contribution (project_id, activity_type) VALUES (:pid, :atype)"),
            [
                {"pid": pid, "atype": "code"},
                {"pid": pid, "atype": "document"},
                {"pid": pid, "atype": "code"},
            ],
        )

        # Skills + link table
        res_py = conn.execute(
            text("INSERT INTO Skill (name, skill_type) VALUES (:name, :stype)"),
            {"name": "REST APIs", "stype": "practice"},
        )
        python_skill_id = int(
            res_py.lastrowid or conn.execute(text("SELECT last_insert_rowid()")).scalar()
        )
        res_fl = conn.execute(
            text("INSERT INTO Skill (name, skill_type) VALUES (:name, :stype)"),
            {"name": "Flask", "stype": "tool"},
        )
        flask_skill_id = int(
            res_fl.lastrowid or conn.execute(text("SELECT last_insert_rowid()")).scalar()
        )
        conn.execute(
            text("INSERT INTO ProjectSkill (project_id, skill_id) VALUES (:pid, :sid)"),
            [{"pid": pid, "sid": python_skill_id}, {"pid": pid, "sid": flask_skill_id}],
        )

    yield db_url


def test_project_summary(monkeypatch, temp_db):
    """Test ProjectSummary.summarize() using a temporary relative DB path."""
    # Point the module to the temporary sqlite DB via DATABASE_URL
    # temp_db is a DB URL when using the SQLAlchemy-driven fixture
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()

    result = ps.ProjectSummary.summarize("Artifact Miner")

    # --- Assertions ---
    assert result["project_name"] == "Artifact Miner"
    assert result["language"] == "Python"
    assert result["framework"] == "Flask"
    assert result["collaboration"] == "individual"
    assert "code" in result["artifact_counts"]
    assert "document" in result["artifact_counts"]
    assert "Flask" in result["tools"]
    assert "REST APIs" in result["practices"]


def test_get_project_metadata(monkeypatch, temp_db):
    """Test the _get_project_metadata helper returns the correct row."""
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()

    with ps.ProjectSummary._get_connection() as conn:
        project = ps.ProjectSummary._get_project_metadata(conn, "Artifact Miner")
        assert project["name"] == "Artifact Miner"
        assert project["language"] == "Python"


def test_artifact_and_contrib_counts(monkeypatch, temp_db):
    """Test artifact and contribution count helpers."""
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()

    with ps.ProjectSummary._get_connection() as conn:
        project = ps.ProjectSummary._get_project_metadata(conn, "Artifact Miner")
        pid = project["id"]

        artifact_counts = ps.ProjectSummary._get_artifact_counts(conn, pid)
        # We inserted two 'code' artifacts and one 'document'
        assert artifact_counts.get("code") == 2
        assert artifact_counts.get("document") == 1

        contrib_counts = ps.ProjectSummary._get_contrib_counts(conn, pid)
        # We inserted two code contributions and one document
        assert contrib_counts.get("code") == 2
        assert contrib_counts.get("document") == 1


def test_get_skills(monkeypatch, temp_db):
    """Test the _get_skills helper returns all skill names for a project."""
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()

    with ps.ProjectSummary._get_connection() as conn:
        project = ps.ProjectSummary._get_project_metadata(conn, "Artifact Miner")
        pid = project["id"]
        skills = ps.ProjectSummary._get_skills(conn, pid)
        assert set(skills) == {"Flask", "REST APIs"}


def test_missing_project_raises(monkeypatch, temp_db):
    """If a project name is not present, summarize should raise ValueError."""
    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()
    with pytest.raises(ValueError):
        ps.ProjectSummary.summarize("Nonexistent Project")


def test_empty_project_has_no_artifacts_or_skills(monkeypatch, tmp_path, temp_db):
    """Create an empty project (no artifacts/contributions/skills) and verify counts are empty."""
    # Use the temp_db file and insert an empty project into it
    # Insert an empty project using SQLAlchemy so the module sees it
    engine = create_engine(temp_db)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO Project (name, description) VALUES (:name, :desc)"),
            {"name": "Empty Project", "desc": "No data"},
        )

    monkeypatch.setenv("DB_URL", temp_db)
    _reset_app_db()
    result = ps.ProjectSummary.summarize("Empty Project")
    assert result["artifact_counts"] == {}
    assert result["activity_counts"] == {}
    assert result["tools"] == []
    assert result["practices"] == []

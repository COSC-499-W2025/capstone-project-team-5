import sqlite3

import pytest

import outputs.project_summary as ps


@pytest.fixture
def temp_db(tmp_path):
    # Create a temporary SQLite database.
    # Populate it with minimal schema and test data.
    db_path = tmp_path / "test_artifact_miner.db"
    conn = sqlite3.connect(db_path)
    # Ensure foreign key support for cascade behavior if used by code
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # Create tables
    cur.executescript("""
    CREATE TABLE Project (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        is_collaborative BOOLEAN NOT NULL DEFAULT 0,
        start_date DATE,
        end_date DATE,
        language TEXT,
        framework TEXT,
        importance_rank INTEGER
    );
    CREATE TABLE Artifact (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        path TEXT NOT NULL,
        type TEXT NOT NULL
    );
    CREATE TABLE Contribution (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        artifact_id INTEGER,
        activity_type TEXT NOT NULL,
        date DATE,
        description TEXT
    );
    CREATE TABLE Skill (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    CREATE TABLE ProjectSkill (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL
    );
    """)

    # Insert a test project
    cur.execute(
        """
        INSERT INTO Project (
            name,
            description,
            language,
            framework,
            is_collaborative,
            start_date,
            end_date,
            importance_rank
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Artifact Miner",
            "Testing project summary output",
            "Python",
            "Flask",
            0,
            "2024-09-01",
            "2024-12-01",
            1,
        ),
    )

    pid = cur.lastrowid

    # Artifacts
    cur.executemany(
        "INSERT INTO Artifact (project_id, path, type) VALUES (?,?,?)",
        [
            (pid, "src/main.py", "code"),
            (pid, "tests/test_main.py", "code"),
            (pid, "docs/readme.md", "document"),
        ],
    )

    # Contributions
    cur.executemany(
        "INSERT INTO Contribution (project_id, activity_type) VALUES (?,?)",
        [(pid, "code"), (pid, "document"), (pid, "code")],
    )

    # Skills + link table
    cur.executemany("INSERT INTO Skill (name) VALUES (?)", [("Python",), ("Flask",)])
    cur.executemany(
        "INSERT INTO ProjectSkill (project_id, skill_id) VALUES (?,?)", [(pid, 1), (pid, 2)]
    )

    conn.commit()
    conn.close()
    yield db_path


def test_project_summary(monkeypatch, temp_db):
    """Test ProjectSummary.summarize() using a temporary relative DB path."""
    # ProjectSummary expects DB_PATH to be a Path-like; ensure we provide that
    monkeypatch.setattr(ps, "DB_PATH", temp_db)

    result = ps.ProjectSummary.summarize("Artifact Miner")

    # --- Assertions ---
    assert result["project_name"] == "Artifact Miner"
    assert result["language"] == "Python"
    assert result["framework"] == "Flask"
    assert result["collaboration"] == "individual"
    assert "code" in result["artifact_counts"]
    assert "document" in result["artifact_counts"]
    assert "Python" in result["skills"]
    assert "Flask" in result["skills"]

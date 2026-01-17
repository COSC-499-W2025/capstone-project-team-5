from __future__ import annotations

from pathlib import Path

import pytest

import capstone_project_team_5.data.db as app_db
from capstone_project_team_5.data.db import init_db


@pytest.fixture(autouse=True)
def api_db(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, tmp_path: Path) -> None:
    """Use a temporary SQLite DB for API tests."""
    test_file = str(request.fspath)
    if "test_api.py" not in test_file and "test_projects_api.py" not in test_file:
        return

    db_path = tmp_path / "api.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path.as_posix()}")
    app_db._engine = None
    app_db._SessionLocal = None
    init_db()
    yield
    # Dispose engine to release connections
    if app_db._engine is not None:
        app_db._engine.dispose()
        app_db._engine = None
        app_db._SessionLocal = None

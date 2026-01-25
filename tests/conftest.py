from __future__ import annotations

from pathlib import Path

import pytest

import capstone_project_team_5.data.db as app_db
from capstone_project_team_5.data.db import init_db


@pytest.fixture
def api_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Use a temporary SQLite DB for API tests."""
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("DB_URL", f"sqlite:///{db_path.as_posix()}")
    upload_root = tmp_path / "uploads"
    monkeypatch.setenv("ZIP2JOB_UPLOAD_DIR", upload_root.as_posix())
    app_db._engine = None
    app_db._SessionLocal = None
    init_db()
    yield
    # Dispose engine to release connections
    if app_db._engine is not None:
        app_db._engine.dispose()
        app_db._engine = None
        app_db._SessionLocal = None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Automatically add api_db fixture to tests in API test files."""
    for item in items:
        # Check if test file name contains "api" (case-insensitive)
        test_file_path = Path(str(item.fspath))
        if "api" in test_file_path.stem.lower():
            # Automatically add the api_db fixture using usefixtures marker
            item.add_marker(pytest.mark.usefixtures("api_db"))

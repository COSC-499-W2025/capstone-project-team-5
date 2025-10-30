from __future__ import annotations

import json
from pathlib import Path

from capstone_project_team_5.detection import identify_language_and_framework


def test_unknown_when_empty(tmp_path: Path) -> None:
    language, framework = identify_language_and_framework(tmp_path)
    assert language == "Unknown"
    assert framework is None


def test_detect_python_fastapi_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
        [project]
        name = "sample"
        version = "0.0.1"
        dependencies = [
          "fastapi>=0.110",
          "uvicorn"
        ]
        """.strip(),
        encoding="utf-8",
    )

    language, framework = identify_language_and_framework(tmp_path)
    assert language == "Python"
    assert framework == "FastAPI"


def test_detect_js_react_from_package_json(tmp_path: Path) -> None:
    pkg = {
        "name": "webapp",
        "version": "1.0.0",
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
        },
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.js").write_text("console.log('hello')\n", encoding="utf-8")

    language, framework = identify_language_and_framework(tmp_path)
    assert language in {"JavaScript", "TypeScript"}
    assert framework == "React"


def test_detect_python_from_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("flask==3.0.0\n", encoding="utf-8")
    language, framework = identify_language_and_framework(tmp_path)
    assert language == "Python"
    assert framework == "Flask"

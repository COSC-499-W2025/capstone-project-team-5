from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.skill_detection import extract_project_skills


def test_empty_directory_returns_empty_skills(tmp_path: Path) -> None:
    """Test that an empty directory returns no skills."""
    skills = extract_project_skills(tmp_path)
    assert skills["tools"] == set()
    assert skills["practices"] == set()


def test_detect_tools_from_config_files(tmp_path: Path) -> None:
    """Test that tools are detected from configuration files."""
    (tmp_path / "pytest.ini").write_text(
        """
        [pytest]
        testpaths = tests
        """.strip(),
        encoding="utf-8",
    )
    (tmp_path / "ruff.toml").write_text("line-length = 100", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")

    skills = extract_project_skills(tmp_path)
    assert "PyTest" in skills["tools"]
    assert "Ruff" in skills["tools"]
    assert "uv" in skills["tools"]


def test_detect_practices_from_project_structure(tmp_path: Path) -> None:
    """Test that practices are detected from project structure."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text("def test_example(): pass\n", encoding="utf-8")

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text(
        "def add(a: int, b: int) -> int: return a + b\n", encoding="utf-8"
    )

    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("*.pyc\n", encoding="utf-8")

    skills = extract_project_skills(tmp_path)
    assert "Test-Driven Development (TDD)" in skills["practices"]
    assert "Automated Testing" in skills["practices"]
    assert "Modular Architecture" in skills["practices"]
    assert "Documentation Discipline" in skills["practices"]
    assert "Version Control (Git)" in skills["practices"]

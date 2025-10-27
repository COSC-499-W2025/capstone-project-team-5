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


def test_case_insensitive_practice_detection(tmp_path: Path) -> None:
    """Test that case-insensitive practice file names are detected."""
    (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")
    skills_1 = extract_project_skills(tmp_path)
    (tmp_path / "readme.md").write_text("# Project\n", encoding="utf-8")
    skills_2 = extract_project_skills(tmp_path)
    (tmp_path / "ReadMe.md").write_text("# Project\n", encoding="utf-8")
    skills_3 = extract_project_skills(tmp_path)
    assert "Documentation Discipline" in skills_1["practices"]
    assert "Documentation Discipline" in skills_2["practices"]
    assert "Documentation Discipline" in skills_3["practices"]


def test_tool_pattern_detection(tmp_path: Path) -> None:
    """Test that tool file patterns (e.g., .sql) are detected as SQL."""
    (tmp_path / "schema.sql").write_text("CREATE TABLE users;\n", encoding="utf-8")
    (tmp_path / "backup.2025.SQL").write_text("-- SQL backup\n", encoding="utf-8")
    skills = extract_project_skills(tmp_path)
    assert "SQL" in skills["tools"]


def test_practice_path_pattern_detection(tmp_path: Path) -> None:
    """Test that practice path patterns (e.g., docs/, src/, tests/) are detected."""
    (tmp_path / "docs" / "index.md").parent.mkdir()
    (tmp_path / "src" / "main.py").parent.mkdir()
    (tmp_path / "tests" / "test_sample.py").parent.mkdir()
    (tmp_path / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")
    (tmp_path / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "tests" / "test_sample.py").write_text("def test(): pass\n", encoding="utf-8")
    skills = extract_project_skills(tmp_path)
    assert "Documentation Discipline" in skills["practices"]
    assert "Modular Architecture" in skills["practices"]
    assert "Test-Driven Development (TDD)" in skills["practices"]


def test_skip_dirs_are_not_scanned(tmp_path: Path) -> None:
    """Test that files in SKIP_DIRS (e.g., .git, node_modules) are not scanned."""
    skip_dir = tmp_path / ".git"
    skip_dir.mkdir()
    (skip_dir / "Dockerfile").write_text("FROM python:3.11\n", encoding="utf-8")
    skills = extract_project_skills(tmp_path)
    # Should not detect Docker because it's inside .git
    assert "Docker" not in skills["tools"]


def test_tool_directory_pattern_detection(tmp_path: Path) -> None:
    """Test that tool directory patterns (e.g., .github/workflows) are detected."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    skills = extract_project_skills(tmp_path)
    assert "GitHub Actions" in skills["tools"]


def test_practice_file_pattern_detection(tmp_path: Path) -> None:
    """Test that practice file patterns (e.g., pull_request_template) are detected."""
    (tmp_path / "pull_request_template.md").write_text("# PR Template\n", encoding="utf-8")
    skills = extract_project_skills(tmp_path)
    assert "Code Review" in skills["practices"]

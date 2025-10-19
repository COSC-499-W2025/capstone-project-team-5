from __future__ import annotations

from pathlib import Path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _detect_tools(file_path: Path, name: str, root: Path) -> set[str]:
    """
    Detect development tools based on file name and content.
    """
    tools = set()

    if name == "dockerfile" or "docker-compose" in name:
        tools.add("Docker")
    if "pytest" in name or name == "pytest.ini":
        tools.add("PyTest")
    if name == "pyproject.toml" and "[tool.pytest" in _read_text(file_path):
        tools.add("PyTest")
    if "jest" in name:
        tools.add("Jest")
    if "cypress" in name:
        tools.add("Cypress")
    if name.endswith(".sql"):
        tools.add("SQL")
    if name == "uv.lock" or (name == "pyproject.toml" and (root / "uv.lock").exists()):
        tools.add("uv")
    if name == ".pre-commit-config.yaml":
        tools.add("Pre-commit")
    if name == "ruff.toml" or (name == "pyproject.toml" and "[tool.ruff]" in _read_text(file_path)):
        tools.add("Ruff")
    if name.startswith("src-tauri") or name == "tauri.conf.json":
        tools.add("Tauri")

    return tools


def _detect_practices(file_path: Path, name: str, rel: str) -> set[str]:
    """
    Detect software development practices based on file structure and content.
    """
    practices = set()

    # Code quality practices
    if name in (
        ".flake8",
        "pylintrc",
        "mypy.ini",
        "ruff.toml",
        ".eslintrc",
        "prettier.config.js",
    ):
        practices.add("Code Quality Enforcement")
    if name == "ruff.toml" or (name == "pyproject.toml" and "[tool.ruff]" in _read_text(file_path)):
        practices.add("Code Quality Enforcement")

    # Environment management
    if name in ("requirements.txt", "poetry.lock", "Pipfile", ".nvmrc", ".tool-versions"):
        practices.add("Environment Management")

    # Testing practices
    if rel.startswith("tests") or "\\tests\\" in rel or "/tests/" in rel:
        practices.add("Test-Driven Development (TDD)")
        practices.add("Automated Testing")

    # CI/CD
    if ".github/workflows" in rel or ".github\\workflows" in rel or name == "gitlab-ci.yml":
        practices.add("CI/CD")

    # Documentation
    if "docs" in rel or name.startswith("readme"):
        practices.add("Documentation Discipline")

    # API Design
    if name in ("openapi.yaml", "swagger.json") or "/api/" in rel or "\\api\\" in rel:
        practices.add("API Design")

    # Architecture
    if any(f in rel for f in ("src", "core", "domain", "modules")):
        practices.add("Modular Architecture")

    # Type Safety
    if name.endswith(".py") and "def " in _read_text(file_path):
        content = _read_text(file_path)
        if "->" in content or ": " in content:
            practices.add("Type Safety")

    # Version Control
    if name == ".gitignore" or ".git" in rel:
        practices.add("Version Control (Git)")

    # Code Review
    if "pull_request_template" in name:
        practices.add("Code Review")

    # Team Collaboration
    if "logs" in rel or "minutes" in rel:
        practices.add("Team Collaboration")

    return practices


def _scan_project_files(root: Path) -> tuple[set[str], set[str]]:
    """
    Scan all files in the project to detect tools and practices.
    """
    tools = set()
    practices = set()

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        name = file_path.name.lower()
        rel = str(file_path.relative_to(root)).lower()

        tools.update(_detect_tools(file_path, name, root))
        practices.update(_detect_practices(file_path, name, rel))

    return tools, practices


def extract_project_skills(project_root: Path | str) -> dict[str, set[str]]:
    """
    Extracts project skills: tools and practices from the given project root directory.
    """
    root = Path(project_root)
    skills = {
        "tools": set(),
        "practices": set(),
    }

    if not root.exists() or not root.is_dir():
        return skills

    # Scan project files for tools and practices
    tools, practices = _scan_project_files(root)
    skills["tools"].update(tools)
    skills["practices"].update(practices)

    return skills

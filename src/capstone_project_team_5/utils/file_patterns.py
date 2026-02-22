"""File pattern helpers for role and repository analysis."""

from __future__ import annotations

from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import PurePosixPath

INITIALIZATION_FILENAMES: set[str] = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "pom.xml",
    "build.gradle",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "README.md",
}

INFRASTRUCTURE_PATTERNS: tuple[str, ...] = (
    "Dockerfile",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    ".github/workflows/*",
    ".gitlab-ci.yml",
    "Jenkinsfile",
    "*.tf",
    "*.tfvars",
    "k8s/*",
    "helm/*",
    "nginx/*.conf",
    "*.yml",
    "*.yaml",
)

DOCUMENTATION_PATTERNS: tuple[str, ...] = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "docs/*",
    "*.md",
    "*.rst",
)

CODE_EXTENSIONS: set[str] = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".sql",
    ".sh",
}


def normalize_path(path: str) -> str:
    """Normalize file path to POSIX-style for consistent pattern matching."""
    return path.replace("\\", "/").strip()


def is_initialization_file(path: str) -> bool:
    """Return True if a path looks like a project initialization/setup file."""
    normalized = normalize_path(path)
    filename = PurePosixPath(normalized).name
    return filename in INITIALIZATION_FILENAMES


def is_infrastructure_file(path: str) -> bool:
    """Return True if a path looks like architecture/infrastructure config."""
    normalized = normalize_path(path)
    filename = PurePosixPath(normalized).name
    return any(
        fnmatch(normalized, pattern) or fnmatch(filename, pattern)
        for pattern in INFRASTRUCTURE_PATTERNS
    )


def is_documentation_file(path: str) -> bool:
    """Return True if a path looks like documentation content."""
    normalized = normalize_path(path)
    filename = PurePosixPath(normalized).name
    return any(fnmatch(normalized, pattern) or fnmatch(filename, pattern) for pattern in DOCUMENTATION_PATTERNS)


def is_code_file(path: str) -> bool:
    """Return True if a path likely represents source code."""
    normalized = normalize_path(path)
    suffix = PurePosixPath(normalized).suffix.lower()
    return suffix in CODE_EXTENSIONS


def count_matches(paths: list[str], predicate: Callable[[str], bool]) -> int:
    """Count how many paths satisfy predicate."""
    return sum(1 for path in paths if predicate(path))

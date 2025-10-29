"""Git related utilities."""

from __future__ import annotations

from pathlib import Path


def is_git_repo(path: Path) -> bool:
    """Return True when ``path`` contains a Git repository."""

    return path.joinpath(".git").is_dir()

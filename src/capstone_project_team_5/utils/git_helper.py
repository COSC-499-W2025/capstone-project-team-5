"""Git Related Utility Helper methods."""

from __future__ import annotations

import subprocess
from pathlib import Path


def is_git_repo(root: Path) -> bool:
    """
    Returns true if root is located within a Git working tree.

    Args:
        root: Project root directory.

    Returns:
        bool: Returns if root is inside a git directory.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except (OSError, ValueError):
        return False


def run_git_command(command: str, root: Path) -> str:
    """
    Uses subprocess.run to execute the given Git
    command in the specified root directory and
    returns it's output as a string. Returns an
    empty string if failure occurs.

    Args:
        command: String of the command to run.
        root: Project root directory.

    Returns:
        String: Result of the command.

    """
    if not is_git_repo(root):
        return ""

    command_args = ["git"] + command.split()

    try:
        result = subprocess.run(
            command_args,
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    except subprocess.CalledProcessError:
        return ""

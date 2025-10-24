"""Contributor analysis module for identifying authorship in git repositories.

This module extends the project analysis capabilities to include git authorship
information, allowing users to differentiate their contributions from others'.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ContributorInfo:
    """Information about a contributor's work in the repository.

    Attributes:
        name: Contributor's name.
        email: Contributor's email.
        commits: Number of commits.
        files_modified: Number of unique files modified.
    """

    name: str
    email: str
    commits: int = 0
    files_modified: int = 0


class ContributorDetector:
    """Detector for git repository contributor statistics."""

    @staticmethod
    def _is_git_repository(directory: Path) -> bool:
        """Check if a directory contains a .git folder.

        Args:
            directory: Path to check.

        Returns:
            True if directory is a git repository, False otherwise.
        """
        return (directory / ".git").exists() and (directory / ".git").is_dir()

    @staticmethod
    def _run_git_command(repo_path: Path, args: list[str]) -> str:
        """Execute a git command and return its output.

        Args:
            repo_path: Path to the git repository.
            args: Git command arguments.

        Returns:
            Command output as string.

        Raises:
            ValueError: If git command fails.
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Git command failed: {e}") from e

    @staticmethod
    def _parse_shortlog(output: str) -> dict[str, ContributorInfo]:
        """Parse git shortlog output into contributor information.

        Args:
            output: Output from git shortlog command.

        Returns:
            Dictionary mapping emails to ContributorInfo objects.
        """
        contributors: dict[str, ContributorInfo] = {}

        for line in output.split("\n"):
            if not line.strip():
                continue

            # Format: "   123  Name <email>"
            parts = line.strip().split("\t")
            if len(parts) != 2:
                continue

            commits = int(parts[0].strip())
            author_info = parts[1].strip()

            if "<" in author_info and ">" in author_info:
                name = author_info[: author_info.index("<")].strip()
                email = author_info[author_info.index("<") + 1 : author_info.index(">")]
            else:
                name = author_info
                email = "unknown"

            contributors[email] = ContributorInfo(name=name, email=email, commits=commits)

        return contributors

    @staticmethod
    def _count_files_per_contributor(
        repo_path: Path, contributors: dict[str, ContributorInfo]
    ) -> None:
        """Count unique files modified by each contributor.

        Args:
            repo_path: Path to the git repository.
            contributors: Dictionary of contributors to update.
        """
        for email, info in contributors.items():
            try:
                output = ContributorDetector._run_git_command(
                    repo_path, ["log", "--author", email, "--name-only", "--pretty=format:"]
                )
                files = {line for line in output.split("\n") if line.strip()}
                info.files_modified = len(files)
            except ValueError:
                # If command fails, keep files_modified at 0
                pass

    @staticmethod
    def _get_all_contributors(repo_path: Path) -> dict[str, ContributorInfo]:
        """Get all contributors from a git repository.

        Args:
            repo_path: Path to the git repository.

        Returns:
            Dictionary mapping emails to ContributorInfo objects.

        Raises:
            ValueError: If not a git repository.
        """
        if not ContributorDetector._is_git_repository(repo_path):
            raise ValueError(f"{repo_path} is not a git repository")

        output = ContributorDetector._run_git_command(repo_path, ["shortlog", "-sne", "--all"])
        contributors = ContributorDetector._parse_shortlog(output)
        ContributorDetector._count_files_per_contributor(repo_path, contributors)

        return contributors


def analyze_contributors(
    project_root: Path | str, merge_duplicates: bool = True
) -> dict[str, list[ContributorInfo]]:
    """Analyze git contributors in a project directory.

    Args:
        project_root: Path to the project directory.
        merge_duplicates: If True, merge contributors with the same name but different emails.

    Returns:
        Dictionary with 'contributors' key containing list of ContributorInfo objects,
        sorted by commit count (descending). Returns empty list if not a git repository.
    """
    root = Path(project_root)
    result = {"contributors": []}

    if not root.exists() or not root.is_dir():
        return result

    try:
        contributors_dict = ContributorDetector._get_all_contributors(root)
        contributors_list = list(contributors_dict.values())

        # Merge duplicates by name if requested
        if merge_duplicates:
            merged: dict[str, ContributorInfo] = {}
            for contrib in contributors_list:
                # Normalize name for comparison (case-insensitive, strip whitespace)
                normalized_name = contrib.name.strip().lower()

                if normalized_name in merged:
                    # Merge with existing entry
                    existing = merged[normalized_name]
                    existing.commits += contrib.commits
                    existing.files_modified += contrib.files_modified
                    # Keep the shorter/cleaner email if available
                    if "@users.noreply.github.com" in existing.email and (
                        "@users.noreply.github.com" not in contrib.email
                    ):
                        existing.email = contrib.email
                else:
                    # Add new entry
                    merged[normalized_name] = ContributorInfo(
                        name=contrib.name,
                        email=contrib.email,
                        commits=contrib.commits,
                        files_modified=contrib.files_modified,
                    )

            contributors_list = list(merged.values())

        # Sort by commits (descending)
        contributors_list.sort(key=lambda x: x.commits, reverse=True)
        result["contributors"] = contributors_list
    except ValueError:
        # Not a git repository or git command failed
        pass

    return result

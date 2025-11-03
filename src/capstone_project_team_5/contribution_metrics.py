from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

from capstone_project_team_5.constants.contribution_metrics_constants import (
    CONTRIBUTION_CATEGORIES,
    SKIP_DIRS,
)
from capstone_project_team_5.utils.git_helper import is_git_repo, run_git_command


class ContributionMetrics:
    """
    Extracts key contribution metrics such as project
    duration and contribution frequency from a
    given project.
    """

    @staticmethod
    def get_project_duration(root: Path) -> tuple[timedelta, str]:
        """
        Returns project duartion for the given project, choosing
        between Git-based or filesystem-based analysis depending
        on the project type.

        Args:
            root: Project root directory.

        Returns:
            Tuple: Project duration and formatted string.
        """

        # Sequential fallback, test for Git repo first

        if is_git_repo(root):
            return ContributionMetrics._get_git_project_duration(root=root)

        return ContributionMetrics._get_non_git_project_duration(root=root)

    @staticmethod
    def get_project_contribution_metrics(root: Path) -> dict[str, int]:
        """
        Returns contribution metrics (e.g., code vs test vs design vs document)
        for the given project, choosing between Git-based or filesystem-based
        analysis depending on the project type.

        Args:
            root: Project root directory.

        Returns:
            dict[str, int] Contribution type with frequency.
        """

        # Sequential fallback, test for Git repo first.

        if is_git_repo(root):
            return ContributionMetrics._get_git_contribution_metrics(root=root)

        return ContributionMetrics._get_non_git_contribution_metrics(root=root)

    @staticmethod
    def _get_git_project_duration(root: Path) -> tuple[timedelta, str]:
        """
        Returns the duration between the initial and
        most recent commit for the given Git project,
        along with a readable string.

        Args:
            root: Project root directory.

        Returns:
            Tuple: Project duration and formatted string.
        """

        git_command: str = "log --all --pretty=format:%ad --date=iso"

        output = run_git_command(command=git_command, root=root)

        if output == "":
            return timedelta(0), "Failed running command."

        commit_dates = [
            datetime.fromisoformat(line.strip()) for line in output.splitlines() if line.strip()
        ]

        start_time = min(commit_dates)
        end_time = max(commit_dates)

        duration: timedelta = end_time - start_time

        formatted = f"Started: {start_time.date()}, Ended: {end_time.date()}"

        return duration, formatted

    @staticmethod
    def _get_non_git_project_duration(root: Path) -> tuple[timedelta, str]:
        """
        Returns the duration between the initial and
        most recent commit for the given non-Git project,
        along with a readable string.

        Args:
            root: Project root directory.

        Returns:
            Tuple: Project duration and formatted string.
        """

        all_files = [
            f
            for f in root.rglob("*")
            if f.is_file()
            and not any(part.lower() in SKIP_DIRS for part in f.parts)
            and not f.name.startswith(".")
        ]

        timestamps = []

        for file in all_files:
            try:
                stat = file.stat()

                if not stat:
                    continue

                created_at = getattr(stat, "st_birthtime", None)
                if created_at is None:
                    created_at = stat.st_ctime

                modified_at = stat.st_mtime

                if created_at:
                    timestamps.append(datetime.fromtimestamp(created_at, tz=UTC))

                if modified_at:
                    timestamps.append(datetime.fromtimestamp(modified_at, tz=UTC))

            except OSError:
                continue

        if not timestamps:
            return timedelta(0), "No files found."

        start_time = min(timestamps)
        end_time = max(timestamps)

        duration: timedelta = end_time - start_time

        formatted = f"Started: {start_time.date()}, Ended: {end_time.date()}"

        return duration, formatted

    @staticmethod
    def _get_file_category(filepath: str) -> str:
        """
        Classifies a file path into a category (code, test, design, document, etc.)
        based on regex patterns defined in CONTRIBUTION_CATEGORIES.
        """
        for category, patterns in CONTRIBUTION_CATEGORIES.items():
            if any(re.search(pattern, filepath, re.IGNORECASE) for pattern in patterns):
                return category
        return "other"

    @staticmethod
    def _get_git_contribution_metrics(root: Path) -> dict[str, int]:
        """
        Analyzes Git commit history to classify contributions
        by activity type.

        Args:
            root: Project root directory.

        Returns:
            dict[str, int] Contribution type with frequency.
        """

        command = "log --name-only --pretty=format: --no-merges --all"
        output = run_git_command(command, root)

        if output == "":
            return {}

        files_changed = [line.strip() for line in output.splitlines() if line.strip()]

        category_counts: Counter = Counter()

        for file in files_changed:
            category = ContributionMetrics._get_file_category(file)
            category_counts[category] += 1

        return dict(category_counts)

    @staticmethod
    def _get_non_git_contribution_metrics(root: Path) -> dict[str, int]:
        """
        Finds contribution frequency for non-Git
        project types.

        Args:
            root: Project root directory.

        Returns:
            dict[str, int] Contribution type with frequency.
        """
        category_counts = Counter()

        all_files = [
            f
            for f in root.rglob("*")
            if f.is_file() and not any(part.lower() in SKIP_DIRS for part in f.parts)
        ]

        for file in all_files:
            category = ContributionMetrics._get_file_category(str(file.relative_to(root)))
            category_counts[category] += 1

        return dict(category_counts)

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
    def _format_project_duration(start_time: datetime, end_time: datetime) -> tuple[timedelta, str]:
        """
        Helper method to format project duration string output.

        Args:
            start_time: Datetime object.
            end_time: Datetime object.

        Returns:
            tuple: Timedelta duration and formatted string duration.
        """
        duration: timedelta = end_time - start_time
        days = duration.days

        years, rem_days = divmod(days, 365)
        months, days = divmod(rem_days, 30)

        parts = []

        if years:
            parts.append(f"{years} year{'s' if years > 1 else ''}")
        if months:
            parts.append(f"{months} month{'s' if months > 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if days > 1 else ''}")

        readable_duration = " ".join(parts) if parts else "0 days"
        formatted = f"{readable_duration} (Started: {start_time.date()} → Ended: {end_time.date()})"

        return duration, formatted

    @staticmethod
    def format_contribution_metrics(metrics: dict[str, int], source: str) -> str:
        """
        Formats the contribution metrics for a project
        into a readable string for CLI output.

        Args:
            metrics: Dictionary mapping contribution types to their counts.
            source: Description of metric source (e.g., "based on Git commits").

        Returns:
            A human-readable string summarizing contribution metrics.
        """

        if not metrics:
            return "📉 No contribution data found."

        emoji_map = {
            "code": "💻",
            "test": "🧪",
            "devops": "⚙️ ",
            "document": "📄",
            "design": "🎨",
            "data": "📊",
        }

        formatted_lines = []

        for key, value in sorted(metrics.items(), key=lambda kv: kv[1], reverse=True):
            emoji = emoji_map.get(key, "•")
            formatted_lines.append(f"{emoji} {key.capitalize()}: {value}")

        metrics_str = ", ".join(formatted_lines)

        return f"Metrics {source}: {metrics_str}"

    @staticmethod
    def get_project_duration(root: Path) -> tuple[timedelta, str]:
        """
        Returns project duration for the given project, choosing
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
    def get_project_contribution_metrics(root: Path) -> tuple[dict[str, int], str]:
        """
        Returns contribution metrics (e.g., code vs test vs design vs document)
        for the given project, choosing between Git-based or filesystem-based
        analysis depending on the project type.

        Args:
            root: Project root directory.

        Returns:
            tuple[dict[str, int], str] Dict with contribution type and frequency and their source.
        """

        # Sequential fallback, test for Git repo first.

        if is_git_repo(root):
            metrics = ContributionMetrics._get_git_contribution_metrics(root=root)
            source = "based on Git commits"
        else:
            metrics = ContributionMetrics._get_non_git_contribution_metrics(root=root)
            source = "based on file counts"

        return metrics, source

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

        return ContributionMetrics._format_project_duration(
            start_time=start_time, end_time=end_time
        )

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

        return ContributionMetrics._format_project_duration(
            start_time=start_time, end_time=end_time
        )

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

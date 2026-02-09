from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from capstone_project_team_5.constants.contribution_metrics_constants import (
    CONTRIBUTION_CATEGORIES,
    SKIP_DIRS,
)
from capstone_project_team_5.utils.git import (
    is_git_repo,
    list_changed_files,
    list_commit_dates,
)


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
    def get_project_dates(root: Path) -> tuple[date | None, date | None]:
        """
        Returns git based start and end dates.

        Returns:
            Tuple of (start_date, end_date) as date objects, or (None, None) if unavailable.
        """

        start_dt, end_dt = ContributionMetrics._get_git_project_duration(root, dates=True)

        if start_dt is None or end_dt is None:
            return None, None

        return start_dt.date(), end_dt.date()

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
    def _get_git_project_duration(root: Path, dates: bool = False) -> tuple:
        """
        Returns the duration between the initial and
        most recent commit for the given Git project,
        along with a readable string.

        Args:
            root: Project root directory.
            dates: If true returns start and end date tuple.

        Returns:
            Tuple: Project duration and formatted string, OR
                (start_datetime, end_datetime) if dates=True
        """

        try:
            commit_dates = list_commit_dates(root, rev_range="--all")
        except RuntimeError:
            if dates:
                return None, None
            return timedelta(0), "Failed running command."

        start_time = min(commit_dates)
        end_time = max(commit_dates)

        if dates:
            return start_time, end_time

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

        try:
            files_changed = list_changed_files(root, all=True, include_merges=False)
        except RuntimeError:
            return {}

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

    @staticmethod
    def calculate_importance_score(
        metrics: dict[str, int], duration: timedelta, file_count: int
    ) -> tuple[float, dict[str, float]]:
        """
        Calculate an importance score for a project based on contribution metrics.

        The score combines multiple factors:
        - Total contribution count (sum of all contribution types)
        - Contribution diversity (number of different contribution types)
        - Project duration (longer projects get higher score)
        - File count (more files = higher score)

        Args:
            metrics: Dictionary mapping contribution types to their counts.
            duration: Project duration as timedelta.
            file_count: Number of files in the project.

        Returns:
            Tuple of (score, breakdown) where:
            - score: Float score representing project importance (higher = more important)
            - breakdown: Dictionary with component scores for display
        """
        total_contributions = sum(metrics.values()) if metrics else 0

        diversity = len([v for v in metrics.values() if v > 0]) if metrics else 0

        duration_days = max(duration.days, 0)

        duration_score = min(duration_days / 365.0, 1.0) * 100

        file_score = min(file_count / 100.0, 1.0) * 50

        contribution_score = total_contributions * 2.0

        diversity_bonus = diversity * 10.0

        score = contribution_score + diversity_bonus + duration_score + file_score

        breakdown = {
            "contribution_score": contribution_score,
            "diversity_bonus": diversity_bonus,
            "duration_score": duration_score,
            "file_score": file_score,
            "total_contributions": float(total_contributions),
            "diversity_count": float(diversity),
        }

        return score, breakdown

    @staticmethod
    def apply_score_factors(
        breakdown: dict[str, float],
        factors: dict[str, bool] | None = None,
    ) -> tuple[float, dict[str, float]]:
        """Apply on/off factors to the importance score components.

        This helper allows callers (e.g. the TUI) to let users choose
        which components contribute to the final importance score while
        keeping the underlying calculation stable.

        Args:
            breakdown: Original score breakdown from ``calculate_importance_score``.
            factors: Mapping of factor name to a boolean flag. Supported keys:
                - ``\"contribution\"``
                - ``\"diversity\"``
                - ``\"duration\"``
                - ``\"file_count\"``
              When ``None``, all factors are treated as enabled.

        Returns:
            Tuple of (new_score, new_breakdown).
        """
        factors = factors or {}

        def _enabled(name: str) -> bool:
            return bool(factors.get(name, True))

        contrib_score = float(breakdown.get("contribution_score", 0.0))
        diversity_score = float(breakdown.get("diversity_bonus", 0.0))
        duration_score = float(breakdown.get("duration_score", 0.0))
        file_score = float(breakdown.get("file_score", 0.0))

        new_breakdown = dict(breakdown)
        new_breakdown["contribution_score"] = contrib_score if _enabled("contribution") else 0.0
        new_breakdown["diversity_bonus"] = diversity_score if _enabled("diversity") else 0.0
        new_breakdown["duration_score"] = duration_score if _enabled("duration") else 0.0
        new_breakdown["file_score"] = file_score if _enabled("file_count") else 0.0

        new_score = (
            new_breakdown["contribution_score"]
            + new_breakdown["diversity_bonus"]
            + new_breakdown["duration_score"]
            + new_breakdown["file_score"]
        )

        return new_score, new_breakdown

    @staticmethod
    def format_score_breakdown(score: float, breakdown: dict[str, float]) -> str:
        """
        Format the importance score breakdown for CLI display.

        Args:
            score: Total importance score.
            breakdown: Dictionary with component scores.

        Returns:
            Formatted string showing score breakdown.
        """
        lines = [f"⭐ Importance Score: {score:.1f}"]
        lines.append("   Breakdown:")
        contrib_total = breakdown["total_contributions"]
        contrib_score = breakdown["contribution_score"]
        lines.append(f"   • Contributions: {contrib_score:.1f} ({contrib_total:.0f} total)")
        div_bonus = breakdown["diversity_bonus"]
        div_count = breakdown["diversity_count"]
        lines.append(f"   • Diversity Bonus: {div_bonus:.1f} ({div_count:.0f} types)")
        lines.append(f"   • Duration: {breakdown['duration_score']:.1f}")
        lines.append(f"   • File Count: {breakdown['file_score']:.1f}")
        return "\n".join(lines)

    @staticmethod
    def rank_projects(projects: list[tuple[int, float]]) -> list[tuple[int, int]]:
        """
        Assign ranks to projects based on their importance scores.

        Projects are ranked in descending order of score (highest score = rank 1).
        Projects with the same score receive the same rank (ties).

        Args:
            projects: List of (project_id, score) tuples.

        Returns:
            List of (project_id, rank) tuples, sorted by rank ascending.
        """
        if not projects:
            return []

        sorted_projects = sorted(projects, key=lambda x: x[1], reverse=True)

        ranked: list[tuple[int, int]] = []
        current_rank = 1
        previous_score: float | None = None

        for project_id, score in sorted_projects:
            if previous_score is not None and score < previous_score:
                current_rank = len(ranked) + 1
            ranked.append((project_id, current_rank))
            previous_score = score

        return ranked

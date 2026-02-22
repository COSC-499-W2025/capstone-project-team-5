"""User role detection for projects based on contribution patterns.

This module analyzes Git contributions, collaboration data, and file ownership
to determine the user's role in a project (e.g., Lead Developer, Contributor).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from capstone_project_team_5.constants.roles import ProjectRole
from capstone_project_team_5.utils.file_patterns import (
    count_matches,
    is_code_file,
    is_documentation_file,
    is_infrastructure_file,
    is_initialization_file,
)
from capstone_project_team_5.utils.git import (
    AuthorContribution,
    get_commit_type_counts,
    get_weekly_activity,
    run_git,
)


@dataclass
class UserRole:
    """Detected or assigned role for a user in a project.

    Attributes:
        role: Primary role classification
        contribution_percentage: Percentage of total contributions (0-100)
        is_collaborative: Whether project has multiple contributors
        confidence: Confidence level in role detection ("High", "Medium", "Low")
        total_commits: Total commits by user
        total_contributors: Total number of contributors
        justification: Human-readable explanation of role assignment
    """

    role: str
    contribution_percentage: float
    is_collaborative: bool
    confidence: str
    total_commits: int
    total_contributors: int
    justification: str


def detect_user_role(
    project_path: Path,
    current_user: str | None,
    author_contributions: list[AuthorContribution],
    collaborator_count: int,
) -> UserRole | None:
    """Detect user's role based on contribution patterns.

    Analyzes Git commit data to determine the user's role in the project.
    Role is determined by contribution percentage and collaboration context.

    Args:
        project_path: Path to project directory (for future extensions)
        current_user: Current user's Git identity (name or email)
        author_contributions: List of all author contributions from Git
        collaborator_count: Total number of collaborators detected

    Returns:
        UserRole object with detected role, or None if detection fails
    """
    if not current_user or not author_contributions:
        return None

    # Find user's contribution in the list
    user_contrib: AuthorContribution | None = None
    for contrib in author_contributions:
        if _matches_user(contrib.author, current_user):
            user_contrib = contrib
            break

    if not user_contrib:
        return None

    # Calculate contribution percentage
    total_commits = sum(ac.commits for ac in author_contributions)
    total_changes = sum(ac.added + ac.deleted for ac in author_contributions)

    if total_commits == 0 or total_changes == 0:
        return None

    # Use weighted average of commit percentage and change percentage
    commit_pct = (user_contrib.commits / total_commits) * 100
    user_changes = user_contrib.added + user_contrib.deleted
    change_pct = (user_changes / total_changes) * 100 if total_changes > 0 else 0

    # Weight commits slightly higher than changes (commits show authorship intent)
    contribution_pct = commit_pct * 0.6 + change_pct * 0.4

    # Determine role based on contribution and collaboration
    is_collaborative = collaborator_count > 1
    base_role, confidence = _classify_role(
        contribution_pct, is_collaborative, collaborator_count, user_contrib.commits
    )

    # Multi-pass role detection for specialized roles
    role, specialization_reason = _detect_specialized_role(
        project_path=project_path,
        current_user=current_user,
        user_contrib=user_contrib,
        contribution_pct=contribution_pct,
        base_role=base_role,
    )

    # Generate human-readable justification
    justification = _generate_justification(
        contribution_pct, user_contrib.commits, collaborator_count, is_collaborative
    )
    if specialization_reason:
        justification = f"{justification}; {specialization_reason}"

    return UserRole(
        role=role,
        contribution_percentage=round(contribution_pct, 1),
        is_collaborative=is_collaborative,
        confidence=confidence,
        total_commits=user_contrib.commits,
        total_contributors=collaborator_count,
        justification=justification,
    )


def _detect_specialized_role(
    project_path: Path,
    current_user: str,
    user_contrib: AuthorContribution,
    contribution_pct: float,
    base_role: str,
) -> tuple[str, str | None]:
    """Detect specialized roles through additional repository signals.

    Returns:
        tuple of (resolved_role, optional_reason)
    """
    if base_role == ProjectRole.SOLO_DEVELOPER.value:
        return base_role, None

    # Highest-priority specialized signal first.
    if _is_project_creator(project_path, current_user):
        return ProjectRole.PROJECT_CREATOR.value, "identified as earliest project author"

    if _is_tech_lead(project_path, current_user, user_contrib.commits, contribution_pct):
        return ProjectRole.TECH_LEAD.value, "high concentration of infrastructure and architecture changes"

    if _is_documentation_lead(project_path, current_user, user_contrib.commits, contribution_pct):
        return ProjectRole.DOCUMENTATION_LEAD.value, "documentation changes dominate contribution profile"

    if _is_maintainer(project_path, current_user, user_contrib.commits):
        return ProjectRole.MAINTAINER.value, "consistent maintenance activity over time"

    return base_role, None


def _is_project_creator(project_path: Path, current_user: str) -> bool:
    """Heuristic for project creator role.

    Requires earliest detected author match and evidence of setup-file authorship.
    """
    try:
        earliest_author = run_git(project_path, "log", "--reverse", "--format=%an", "--max-count=1").strip()
        if not earliest_author or not _matches_user(earliest_author, current_user):
            return False

        early_files = _get_early_commit_files(project_path, commit_limit=25)
        init_file_count = count_matches(early_files, is_initialization_file)
        return init_file_count > 0
    except RuntimeError:
        return False


def _is_tech_lead(
    project_path: Path,
    current_user: str,
    user_commits: int,
    contribution_pct: float,
) -> bool:
    """Heuristic for tech lead role based on infra/config focus."""
    if user_commits < 3 or contribution_pct < 15.0:
        return False

    files = _get_user_changed_files(project_path, current_user)
    if not files:
        return False

    infra_count = count_matches(files, is_infrastructure_file)
    docs_count = count_matches(files, is_documentation_file)
    infra_ratio = infra_count / len(files)

    # Infra-heavy profile with some supporting docs indicates architecture ownership.
    return infra_count >= 3 and infra_ratio >= 0.35 and docs_count >= 1


def _is_maintainer(project_path: Path, current_user: str, user_commits: int) -> bool:
    """Heuristic for maintainer role using sustained activity and maintenance commits."""
    if user_commits < 6:
        return False

    active_week_count = _get_active_week_count(project_path, current_user)
    if active_week_count < 6:
        return False

    maintenance_commit_ratio = _get_maintenance_commit_ratio(project_path, current_user)
    return maintenance_commit_ratio >= 0.3


def _is_documentation_lead(
    project_path: Path,
    current_user: str,
    user_commits: int,
    contribution_pct: float,
) -> bool:
    """Heuristic for documentation lead based on docs-to-code ratio."""
    if user_commits < 3 or contribution_pct < 10.0:
        return False

    files = _get_user_changed_files(project_path, current_user)
    if not files:
        return False

    docs_count = count_matches(files, is_documentation_file)
    code_count = count_matches(files, is_code_file)

    # Require clear docs ownership, not just occasional README edits.
    return docs_count >= 4 and docs_count > code_count and (docs_count / len(files)) >= 0.5


def _get_early_commit_files(project_path: Path, commit_limit: int = 25) -> list[str]:
    """Get file paths touched in the earliest commits of the repository."""
    try:
        output = run_git(
            project_path,
            "log",
            "--reverse",
            "--name-only",
            "--pretty=format:",
            f"--max-count={commit_limit}",
        )
        return [line.strip() for line in output.splitlines() if line.strip()]
    except RuntimeError:
        return []


def _get_user_changed_files(project_path: Path, current_user: str) -> list[str]:
    """Get file paths touched by the current user."""
    try:
        output = run_git(
            project_path,
            "log",
            "--name-only",
            "--pretty=format:",
            f"--author={current_user}",
            "--no-merges",
        )
        return [line.strip() for line in output.splitlines() if line.strip()]
    except RuntimeError:
        return []


def _get_active_week_count(project_path: Path, current_user: str, weeks: int = 12) -> int:
    """Count number of active weeks with at least one commit for the user."""
    try:
        activity = get_weekly_activity(project_path, weeks=weeks)
    except RuntimeError:
        return 0

    author_weeks: list[int] = []
    for author, counts in activity.items():
        if _matches_user(author, current_user):
            author_weeks = counts
            break

    return sum(1 for count in author_weeks if count > 0)


def _get_maintenance_commit_ratio(project_path: Path, current_user: str) -> float:
    """Return ratio of maintenance-style commits for user.

    Maintenance commits are: fix, chore, docs, refactor.
    """
    try:
        type_counts = get_commit_type_counts(project_path)
    except RuntimeError:
        return 0.0

    user_counts: dict[str, int] = {}
    for author, counts in type_counts.items():
        if _matches_user(author, current_user):
            user_counts = counts
            break

    total = sum(user_counts.values())
    if total == 0:
        return 0.0

    maintenance_total = sum(
        user_counts.get(commit_type, 0)
        for commit_type in ("fix", "chore", "docs", "refactor")
    )
    return maintenance_total / total


def _matches_user(author_name: str, current_user: str) -> bool:
    """Check if author name matches current user (case-insensitive)."""
    return author_name.strip().lower() == current_user.strip().lower()


def _classify_role(
    contribution_pct: float, is_collaborative: bool, collaborator_count: int, user_commits: int
) -> tuple[str, str]:
    """Classify user role based on contribution percentage and context.

    Args:
        contribution_pct: User's contribution percentage (0-100)
        is_collaborative: Whether project has multiple contributors
        collaborator_count: Total number of contributors
        user_commits: Number of commits by user

    Returns:
        Tuple of (role, confidence_level)
    """
    # Solo developer - 100% contribution or only contributor
    if not is_collaborative or contribution_pct >= 99.0:
        confidence = "High" if user_commits >= 5 else "Medium"
        return ProjectRole.SOLO_DEVELOPER.value, confidence

    # Lead developer - dominant contributor in team project (60-98%)
    if contribution_pct >= 60.0:
        confidence = "High" if user_commits >= 10 else "Medium"
        return ProjectRole.LEAD_DEVELOPER.value, confidence

    # Core contributor - substantial ongoing involvement (40-59%)
    if contribution_pct >= 40.0:
        confidence = "High" if user_commits >= 8 else "Medium"
        return ProjectRole.CORE_CONTRIBUTOR.value, confidence

    # Major contributor - significant but not core (25-39%)
    if contribution_pct >= 25.0:
        confidence = "High" if user_commits >= 5 else "Medium"
        return ProjectRole.MAJOR_CONTRIBUTOR.value, confidence

    # Contributor - moderate involvement (10-24%)
    if contribution_pct >= 10.0:
        confidence = "Medium" if user_commits >= 3 else "Low"
        return ProjectRole.CONTRIBUTOR.value, confidence

    # Minor contributor - small involvement (<10%)
    confidence = "Low"
    return ProjectRole.MINOR_CONTRIBUTOR.value, confidence


def _generate_justification(
    contribution_pct: float,
    user_commits: int,
    collaborator_count: int,
    is_collaborative: bool,
) -> str:
    """Generate human-readable justification for role assignment.

    Args:
        contribution_pct: User's contribution percentage
        user_commits: Number of commits by user
        collaborator_count: Total number of contributors
        is_collaborative: Whether project has multiple contributors

    Returns:
        Human-readable justification string
    """
    commit_str = "commit" if user_commits == 1 else "commits"

    if not is_collaborative:
        return f"Sole author with {user_commits} {commit_str}"

    if collaborator_count == 2:
        collab_str = "1 other contributor"
    else:
        collab_str = f"{collaborator_count - 1} other contributors"

    return (
        f"{user_commits} {commit_str} representing {contribution_pct:.1f}% "
        f"of contributions with {collab_str}"
    )


def format_role_summary(role_info: UserRole | None) -> str:
    """Format role information for display.

    Args:
        role_info: UserRole object or None

    Returns:
        Human-readable role summary string
    """
    if not role_info:
        return "Role: Unknown (insufficient data)"

    if role_info.is_collaborative:
        return (
            f"Role: {role_info.role} "
            f"({role_info.contribution_percentage:.1f}% of contributions, "
            f"{role_info.total_commits} commits)"
        )
    else:
        return f"Role: {role_info.role} ({role_info.total_commits} commits)"

"""User role detection for projects based on contribution patterns.

This module analyzes Git contributions, collaboration data, and file ownership
to determine the user's role in a project (e.g., Lead Developer, Contributor).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from capstone_project_team_5.utils.git import AuthorContribution


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
    role, confidence = _classify_role(
        contribution_pct, is_collaborative, collaborator_count, user_contrib.commits
    )

    # Generate human-readable justification
    justification = _generate_justification(
        role, contribution_pct, user_contrib.commits, collaborator_count, is_collaborative
    )

    return UserRole(
        role=role,
        contribution_percentage=round(contribution_pct, 1),
        is_collaborative=is_collaborative,
        confidence=confidence,
        total_commits=user_contrib.commits,
        total_contributors=collaborator_count,
        justification=justification,
    )


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
        return "Solo Developer", confidence

    # Lead developer - dominant contributor in team project
    if contribution_pct >= 60.0:
        confidence = "High" if user_commits >= 10 else "Medium"
        return "Lead Developer", confidence

    # Major contributor - significant but not lead
    if contribution_pct >= 30.0:
        confidence = "High" if user_commits >= 5 else "Medium"
        return "Major Contributor", confidence

    # Contributor - moderate involvement
    if contribution_pct >= 10.0:
        confidence = "Medium" if user_commits >= 3 else "Low"
        return "Contributor", confidence

    # Minor contributor - small involvement
    confidence = "Low"
    return "Minor Contributor", confidence


def _generate_justification(
    role: str,
    contribution_pct: float,
    user_commits: int,
    collaborator_count: int,
    is_collaborative: bool,
) -> str:
    """Generate human-readable justification for role assignment.

    Args:
        role: Assigned role
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
        return "👤 Role: Unknown (insufficient data)"

    emoji_map = {
        "Solo Developer": "👨‍💻",
        "Lead Developer": "🎯",
        "Major Contributor": "🔧",
        "Contributor": "🤝",
        "Minor Contributor": "✨",
    }

    emoji = emoji_map.get(role_info.role, "👤")

    if role_info.is_collaborative:
        return (
            f"{emoji} Role: {role_info.role} "
            f"({role_info.contribution_percentage:.1f}% of contributions, "
            f"{role_info.total_commits} commits)"
        )
    else:
        return f"{emoji} Role: {role_info.role} ({role_info.total_commits} commits)"

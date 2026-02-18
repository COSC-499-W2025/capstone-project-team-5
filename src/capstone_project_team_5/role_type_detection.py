"""Enhanced role detection based on file types and contribution patterns.

This module extends the basic role detection by analyzing the types of files
contributors work on, enabling detection of specialized roles like:
- Backend Developer (server code, APIs, databases)
- Frontend Developer (UI, components, styling)
- Full Stack Developer (both frontend and backend)
- DevOps Engineer (infrastructure, CI/CD, configs)
- Data Engineer/Scientist (data processing, notebooks, models)
- QA Engineer (tests, test configs)
- Technical Writer (documentation)
- Designer (UI/UX assets, design files)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from capstone_project_team_5.constants.roles import DIRECTORY_PATTERNS, FILE_CATEGORIES
from capstone_project_team_5.utils.git import AuthorContribution, run_git


@dataclass
class FileContribution:
    """File-level contribution statistics for a user."""

    path: str
    commits: int
    added: int
    deleted: int
    category: str | None = None


@dataclass
class CategoryStats:
    """Statistics for a file category."""

    commits: int
    files: int
    lines_changed: int
    percentage: float


@dataclass
class UserRoleType:
    """Enhanced role detection including file-type analysis.

    Attributes:
        primary_role: Main role based on file types worked on
        secondary_roles: Additional roles (for multi-skilled contributors)
        category_breakdown: Percentage breakdown by file category
        specializations: List of detected specializations
        file_focus: Top 3 file types the user works with
        confidence: Confidence level ("High", "Medium", "Low")
        justification: Human-readable explanation
    """

    primary_role: str
    secondary_roles: list[str]
    category_breakdown: dict[str, CategoryStats]
    specializations: list[str]
    file_focus: list[str]
    confidence: str
    justification: str


def get_user_file_contributions(
    repo_path: Path,
    user_name: str,
) -> list[FileContribution]:
    """Get detailed file-level contributions for a specific user.

    Args:
        repo_path: Path to the Git repository
        user_name: Git username to analyze

    Returns:
        List of FileContribution objects for the user
    """

    try:
        output = run_git(
            repo_path, "log", "--numstat", "--pretty=format:%H", f"--author={user_name}"
        )
    except RuntimeError:
        return []

    file_stats: dict[str, FileContribution] = {}

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        # If commit hash ignore
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            continue

        # Parse numstat line: added\tdeleted\tpath
        parts = line.split("\t")
        if len(parts) != 3:
            continue

        added_str, deleted_str, path = parts

        # Skip binary files
        if added_str == "-" or deleted_str == "-":
            continue

        try:
            added = int(added_str)
            deleted = int(deleted_str)
        except ValueError:
            continue

        # Aggregate by file path
        if path not in file_stats:
            file_stats[path] = FileContribution(path=path, commits=0, added=0, deleted=0)

        file_stats[path].commits += 1
        file_stats[path].added += added
        file_stats[path].deleted += deleted

    return list(file_stats.values())


def categorize_file(file_path: str) -> str | None:
    """Determine the category of a file based on its path and extension.

    Args:
        file_path: Path to the file

    Returns:
        Category string or None if unclassified
    """

    path_lower = file_path.lower()
    suffix = Path(file_path).suffix.lower()

    for test_pattern in FILE_CATEGORIES["testing"]:
        if test_pattern in path_lower:
            return "testing"

    # Handle ambiguous models directory by file extension
    if "models/" in path_lower or "/models/" in path_lower:
        backend_extensions = {".py", ".go", ".java", ".rb", ".php", ".rs", ".kt", ".js", ".ts"}
        ml_extensions = {".h5", ".hdf5", ".pkl", ".pickle", ".pt", ".pth", ".onnx", ".joblib"}

        if suffix in backend_extensions:
            return "backend"
        elif suffix in ml_extensions:
            return "data"

    # Handle SQL files based on directory context
    if suffix == ".sql":
        if any(d in path_lower for d in ["data/", "datasets/", "notebooks/", "analytics/"]):
            return "data"
        return "backend"

    # Check directory patterns first
    for category, patterns in DIRECTORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in path_lower:
                return category

    # Check for test file first
    for test_pattern in FILE_CATEGORIES["testing"]:
        if test_pattern in path_lower:
            return "testing"

    # Check each category
    for category, extensions in FILE_CATEGORIES.items():
        if category == "testing":  # Already handled above
            continue
        if suffix in extensions or Path(file_path).name in extensions:
            return category

    return None


def analyze_file_categories(file_contributions: list[FileContribution]) -> dict[str, CategoryStats]:
    """Analyze contributions by file category.

    Args:
        file_contributions: List of file contributions for a user

    Returns:
        Dictionary mapping category to statistics
    """

    category_data: dict[str, dict[str, int]] = defaultdict(
        lambda: {"commits": 0, "files": 0, "lines": 0}
    )

    total_lines = 0

    # Categorize each file and aggregate stats
    for contrib in file_contributions:
        category = categorize_file(contrib.path)
        if category is None:
            category = "other"

        lines_changed = contrib.added + contrib.deleted
        category_data[category]["commits"] += contrib.commits
        category_data[category]["files"] += 1
        category_data[category]["lines"] += lines_changed
        total_lines += lines_changed

    # Convert to CategoryStats with percentages
    stats: dict[str, CategoryStats] = {}
    for category, data in category_data.items():
        percentage = (data["lines"] / total_lines * 100) if total_lines > 0 else 0
        stats[category] = CategoryStats(
            commits=data["commits"],
            files=data["files"],
            lines_changed=data["lines"],
            percentage=round(percentage, 1),
        )

    return stats


def detect_specialized_role(
    category_breakdown: dict[str, CategoryStats], total_commits: int
) -> UserRoleType:
    """Detect specialized role based on file category analysis.

    Args:
        category_breakdown: Statistics by file category
        total_commits: Total number of commits by user

    Returns:
        UserRoleType with detected role and analysis
    """

    # Sort categories by percentage of work
    sorted_categories = sorted(
        category_breakdown.items(), key=lambda x: x[1].percentage, reverse=True
    )

    if not sorted_categories:
        return UserRoleType(
            primary_role="Contributor",
            secondary_roles=[],
            category_breakdown={},
            specializations=[],
            file_focus=[],
            confidence="Low",
            justification="Insufficient file data for role detection",
        )

    # Determine primary role based on dominant category
    primary_category = sorted_categories[0][0]
    primary_percentage = sorted_categories[0][1].percentage

    # Get secondary categories (>15% involvement)
    secondary_categories = [cat for cat, stats in sorted_categories[1:] if stats.percentage >= 15.0]

    # Map categories to roles
    role_mapping = {
        "frontend": "Frontend Developer",
        "backend": "Backend Developer",
        "mobile": "Mobile Developer",
        "devops": "DevOps Engineer",
        "data": "Data Engineer",
        "testing": "QA Engineer",
        "documentation": "Technical Writer",
        "design": "UI/UX Designer",
        "config": "Configuration Manager",
    }

    primary_role = role_mapping.get(primary_category, "Software Developer")
    secondary_roles = [
        role_mapping.get(cat, cat.title() + " Contributor") for cat in secondary_categories
    ]

    # Detect full-stack pattern
    has_frontend = any(
        stats.percentage >= 20 for cat, stats in sorted_categories if cat == "frontend"
    )
    has_backend = any(
        stats.percentage >= 20 for cat, stats in sorted_categories if cat == "backend"
    )

    if has_frontend and has_backend:
        primary_role = "Full Stack Developer"
        secondary_roles = [
            role_mapping.get(cat, cat.title() + " Contributor")
            for cat in secondary_categories
            if cat not in ["frontend", "backend"]
        ]

    # Detect specializations
    specializations = []
    for category, stats in sorted_categories:
        if stats.percentage >= 30.0 and category != primary_category:
            spec = role_mapping.get(category, category.title())
            specializations.append(spec)

    # Get top file focuses
    file_focus = [cat for cat, _ in sorted_categories[:3] if cat != "other"]

    confidence = (
        "High"
        if primary_percentage >= 40.0 and total_commits >= 10
        else "Medium"
        if primary_percentage >= 25.0 and total_commits >= 5
        else "Low"
    )

    focus_str = ", ".join(
        [f"{cat}: {stats.percentage:.1f}%" for cat, stats in sorted_categories[:3]]
    )
    justification = (
        f"Primary focus on {primary_category} files ({primary_percentage:.1f}% of changes). "
        f"Contribution breakdown: {focus_str}"
    )

    if secondary_roles:
        justification += f". Also contributes to: {', '.join(secondary_roles[:2])}"

    return UserRoleType(
        primary_role=primary_role,
        secondary_roles=secondary_roles,
        category_breakdown=category_breakdown,
        specializations=specializations,
        file_focus=file_focus,
        confidence=confidence,
        justification=justification,
    )


def detect_enhanced_user_role(
    project_path: Path, current_user: str | None, author_contributions: list[AuthorContribution]
) -> UserRoleType | None:
    """Main entry point for enhanced role detection.

    Combines contribution-based analysis with file-type analysis to provide
    a more accurate role classification.

    Args:
        project_path: Path to the project repository
        current_user: Current user's Git identity
        author_contributions: List of all author contributions

    Returns:
        UserRoleType or None if detection fails
    """

    if not current_user or not author_contributions:
        return None

    # Find user's contribution data
    user_contrib = None
    for contrib in author_contributions:
        if contrib.author.strip().lower() == current_user.strip().lower():
            user_contrib = contrib
            break

    if not user_contrib:
        return None

    # Get detailed file contributions
    file_contributions = get_user_file_contributions(
        project_path,
        current_user,
    )

    if not file_contributions:
        return None

    # Analyze by category
    category_breakdown = analyze_file_categories(file_contributions)

    # Detect specialized role
    enhanced_role = detect_specialized_role(category_breakdown, user_contrib.commits)

    return enhanced_role


def format_enhanced_role_summary(role_info: UserRoleType | None) -> str:
    """Format enhanced role information for display.

    Args:
        role_info: UserRoleType object or None

    Returns:
        Human-readable role summary string
    """

    if not role_info:
        return "Role: Unknown (insufficient data)"

    summary = f"Role: {role_info.primary_role}"

    if role_info.secondary_roles:
        summary += f" | {', '.join(role_info.secondary_roles[:2])}"

    summary += f" (Confidence: {role_info.confidence})"

    # Add top categories
    if role_info.file_focus:
        summary += f"\nFocus Areas: {', '.join(role_info.file_focus)}"

    return summary

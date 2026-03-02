"""Role taxonomy and metadata for project role detection.

This module defines all possible user roles that can be detected in projects,
along with their associated metadata (emoji, description, priority).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

FILE_CATEGORIES = {
    "frontend": {
        ".jsx",
        ".tsx",
        ".vue",
        ".svelte",
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".styl",
        ".js",
        ".ts",
        ".mjs",  # Can be frontend or backend, context matters
    },
    "backend": {
        ".py",
        ".java",
        ".go",
        ".rb",
        ".php",
        ".rs",
        ".kt",
        ".scala",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".sql",
        ".prisma",
        ".graphql",
    },
    "mobile": {
        ".swift",
        ".m",
        ".mm",  # iOS
        ".kt",
        ".java",  # Android (overlap with backend)
        ".dart",  # Flutter
    },
    "devops": {
        ".yml",
        ".yaml",
        ".tf",
        ".tfvars",  # Terraform
        ".sh",
        ".bash",
        ".zsh",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        ".jenkinsfile",
        ".gitlab-ci.yml",
        ".github",
    },
    "data": {
        ".ipynb",
        ".r",
        ".rmd",
        ".parquet",
        ".csv",
        ".json",
        ".jsonl",
        ".sql",  # Overlap with backend
        ".pkl",
        ".pickle",
    },
    "testing": {
        ".test.js",
        ".test.ts",
        ".test.jsx",
        ".test.tsx",
        ".spec.js",
        ".spec.ts",
        ".spec.jsx",
        ".spec.tsx",
        ".test.py",
        "_test.py",
        ".test.go",
        "_test.go",
        ".test.java",
        "test_*.py",
    },
    "documentation": {
        ".md",
        ".mdx",
        ".rst",
        ".adoc",
        ".txt",
        ".pdf",  # Documentation PDFs
    },
    "design": {
        ".fig",
        ".sketch",
        ".xd",
        ".ai",
        ".psd",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",  # When in design/assets dirs
    },
    "config": {
        ".json",
        ".toml",
        ".ini",
        ".conf",
        ".config",
        ".env",
        ".env.example",
        "package.json",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
    },
}

DIRECTORY_PATTERNS = {
    "frontend": {"src/components", "src/pages", "src/views", "public", "static", "assets/js"},
    "backend": {"src/api", "src/server", "src/services", "src/models", "src/controllers"},
    "devops": {".github/workflows", "infrastructure", "terraform", "ansible", "k8s", "kubernetes"},
    "data": {"notebooks", "data", "datasets", "models", "pipelines"},
    "testing": {"tests", "test", "__tests__", "spec", "e2e", "integration"},
    "documentation": {"docs", "documentation", "wiki"},
    "design": {"design", "designs", "mockups", "assets/images", "assets/icons"},
}


class ProjectRole(StrEnum):
    """Enumeration of all possible project roles.

    Roles are grouped by project responsibility and contribution pattern.
    """

    # Ownership roles
    SOLO_DEVELOPER = "Solo Developer"
    PROJECT_CREATOR = "Project Creator"

    # Leadership roles
    LEAD_DEVELOPER = "Lead Developer"
    TECH_LEAD = "Tech Lead"
    SECURITY_LEAD = "Security Lead"

    # Contribution roles
    CORE_CONTRIBUTOR = "Core Contributor"
    MAJOR_CONTRIBUTOR = "Major Contributor"
    CONTRIBUTOR = "Contributor"
    MINOR_CONTRIBUTOR = "Minor Contributor"

    # Supporting roles
    MAINTAINER = "Maintainer"
    DOCUMENTATION_LEAD = "Documentation Lead"


@dataclass(frozen=True)
class RoleMetadata:
    """Metadata associated with a project role."""

    role: ProjectRole
    description: str
    display_priority: int  # Lower = higher priority for display


# Role metadata mapping
ROLE_METADATA: dict[ProjectRole, RoleMetadata] = {
    ProjectRole.SOLO_DEVELOPER: RoleMetadata(
        role=ProjectRole.SOLO_DEVELOPER,
        description="Sole author and maintainer of the project",
        display_priority=1,
    ),
    ProjectRole.PROJECT_CREATOR: RoleMetadata(
        role=ProjectRole.PROJECT_CREATOR,
        description="Created and initiated the project",
        display_priority=2,
    ),
    ProjectRole.LEAD_DEVELOPER: RoleMetadata(
        role=ProjectRole.LEAD_DEVELOPER,
        description="Primary developer with majority of contributions",
        display_priority=3,
    ),
    ProjectRole.TECH_LEAD: RoleMetadata(
        role=ProjectRole.TECH_LEAD,
        description="Technical leadership with focus on architecture and infrastructure",
        display_priority=4,
    ),
    ProjectRole.SECURITY_LEAD: RoleMetadata(
        role=ProjectRole.SECURITY_LEAD,
        description="Primary owner of application and infrastructure security hardening",
        display_priority=11,
    ),
    ProjectRole.MAINTAINER: RoleMetadata(
        role=ProjectRole.MAINTAINER,
        description="Ongoing maintenance and consistent contributions over time",
        display_priority=5,
    ),
    ProjectRole.DOCUMENTATION_LEAD: RoleMetadata(
        role=ProjectRole.DOCUMENTATION_LEAD,
        description="Primary owner of project documentation and knowledge sharing",
        display_priority=6,
    ),
    ProjectRole.CORE_CONTRIBUTOR: RoleMetadata(
        role=ProjectRole.CORE_CONTRIBUTOR,
        description="Essential contributor with significant ongoing involvement",
        display_priority=7,
    ),
    ProjectRole.MAJOR_CONTRIBUTOR: RoleMetadata(
        role=ProjectRole.MAJOR_CONTRIBUTOR,
        description="Substantial contributions to the project",
        display_priority=8,
    ),
    ProjectRole.CONTRIBUTOR: RoleMetadata(
        role=ProjectRole.CONTRIBUTOR,
        description="Regular contributor to the project",
        display_priority=9,
    ),
    ProjectRole.MINOR_CONTRIBUTOR: RoleMetadata(
        role=ProjectRole.MINOR_CONTRIBUTOR,
        description="Limited contributions to the project",
        display_priority=10,
    ),
}


def get_role_description(role: str | ProjectRole) -> str:
    """Get the description for a given role.

    Args:
        role: Role name or ProjectRole enum

    Returns:
        Description string for the role, or default description if not found
    """
    if isinstance(role, str):
        try:
            role = ProjectRole(role)
        except ValueError:
            return "Unknown role"

    metadata = ROLE_METADATA.get(role)
    return metadata.description if metadata else "Unknown role"


def get_role_priority(role: str | ProjectRole) -> int:
    """Get the display priority for a given role.

    Args:
        role: Role name or ProjectRole enum

    Returns:
        Display priority (lower = higher priority)
    """
    if isinstance(role, str):
        try:
            role = ProjectRole(role)
        except ValueError:
            return 99

    metadata = ROLE_METADATA.get(role)
    return metadata.display_priority if metadata else 99

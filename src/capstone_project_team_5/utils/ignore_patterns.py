from __future__ import annotations

from capstone_project_team_5.consent_tool import ConsentTool


def get_default_ignore_patterns(consent_tool: ConsentTool | None = None) -> list[str]:
    """Return default ignore patterns using the ConsentTool helper."""

    tool = consent_tool or ConsentTool()
    return tool._get_default_ignore_patterns()

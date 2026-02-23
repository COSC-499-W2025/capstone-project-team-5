"""Template registry for resume generation."""

from __future__ import annotations

from capstone_project_team_5.templates.base import ResumeTemplate
from capstone_project_team_5.templates.jake import JakeResumeTemplate
from capstone_project_team_5.templates.modern import ModernResumeTemplate
from capstone_project_team_5.templates.rover import RoverResumeTemplate

__all__ = [
    "ResumeTemplate",
    "get_template",
    "list_templates",
]

_REGISTRY: dict[str, ResumeTemplate] = {
    "jake": JakeResumeTemplate(),
    "modern": ModernResumeTemplate(),
    "rover": RoverResumeTemplate(),
}


def get_template(name: str) -> ResumeTemplate:
    """Return the template registered under *name*.

    Raises:
        ValueError: If no template with that name exists.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY))
        msg = f"Unknown template {name!r}. Available: {available}"
        raise ValueError(msg) from None


def list_templates() -> list[str]:
    """Return sorted names of all registered templates."""
    return sorted(_REGISTRY)

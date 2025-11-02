from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.services.llm import generate_bullet_points_from_analysis
from capstone_project_team_5.services.llm_providers import LLMError
from capstone_project_team_5.skill_detection import extract_project_skills


def generate_ai_bullets_for_project(project_root: Path | str, *, max_bullets: int = 6) -> list[str]:
    """Generate AI bullet points describing a project directory.

    Uses detection and skill extraction, then calls the LLM helper. Returns an
    empty list if the environment is not configured for Gemini or if the LLM
    call fails.
    """
    root = Path(project_root)
    language, framework = identify_language_and_framework(root)
    skills_map = extract_project_skills(root)
    tools: Sequence[str] = sorted(skills_map.get("tools", set()))
    practices: Sequence[str] = sorted(skills_map.get("practices", set()))
    combined = sorted(set(tools) | set(practices))

    try:
        return generate_bullet_points_from_analysis(
            language=language,
            framework=framework,
            skills=combined,
            tools=tools,
            max_bullets=max_bullets,
        )
    except LLMError:
        return []

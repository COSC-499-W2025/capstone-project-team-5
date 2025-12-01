"""
Unified bullet generation with AI/local fallback logic.

This module provides the main entry point for generating resume bullets.
It properly implements the fallback flow:
1. Try AI generation first (if consent given and API available)
2. Fall back to local generation if AI fails or unavailable
3. Use aggregated analysis from all analyzers
"""

from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.services.project_analysis import ProjectAnalysis, analyze_project


def generate_resume_bullets(
    project_path: Path | str,
    *,
    max_bullets: int = 6,
    use_ai: bool = True,
    ai_available: bool = True,
    analysis: ProjectAnalysis | None = None,
) -> tuple[list[str], str]:
    """Generate resume bullets with proper AI/local fallback.

    This is the main entry point for bullet generation. It:
    1. Uses pre-computed analysis if provided, otherwise runs analysis
    2. Tries AI generation if permitted
    3. Falls back to local generation if needed
    4. Returns bullets and source indicator

    Args:
        project_path: Path to project directory
        max_bullets: Maximum number of bullets to generate
        use_ai: Whether AI generation is allowed (consent)
        ai_available: Whether AI API is configured
        analysis: Optional pre-computed ProjectAnalysis (avoids redundant analysis)

    Returns:
        Tuple of (bullets list, source) where source is "AI" or "Local"
    """
    project_path = Path(project_path)

    # Step 1: Use provided analysis or run it if not provided
    if analysis is None:
        analysis = analyze_project(project_path)

    # Step 2: Try AI first if allowed and available
    if use_ai and ai_available:
        ai_bullets = _try_ai_generation(analysis, max_bullets)
        if ai_bullets:
            return _append_testing_bullet(ai_bullets, analysis), "AI"

    # Step 3: Fall back to local generation
    local_bullets = _generate_local_bullets(analysis, max_bullets)
    return _append_testing_bullet(local_bullets, analysis), "Local"


def _try_ai_generation(analysis: ProjectAnalysis, max_bullets: int) -> list[str]:
    """Try to generate bullets using AI/LLM.

    Args:
        analysis: Complete project analysis
        max_bullets: Maximum bullets to generate

    Returns:
        List of bullets, or empty list if AI generation fails
    """
    try:
        from capstone_project_team_5.services.llm import generate_bullet_points_from_analysis

        # Combine all detected skills for AI
        all_skills = (
            analysis.tools
            | analysis.practices
            | analysis.technical_features
            | analysis.oop_features
            | analysis.design_patterns
            | analysis.data_structures
            | analysis.algorithms
        )

        return generate_bullet_points_from_analysis(
            language=analysis.language,
            framework=analysis.framework,
            skills=sorted(all_skills),
            tools=sorted(analysis.tools),
            max_bullets=max_bullets,
        )
    except (ImportError, Exception):  # LLMError or any other error
        return []


def _generate_local_bullets(analysis: ProjectAnalysis, max_bullets: int) -> list[str]:
    """Generate bullets using local analysis (no AI).

    Args:
        analysis: Complete project analysis
        max_bullets: Maximum bullets to generate

    Returns:
        List of professionally-written resume bullets
    """
    from capstone_project_team_5.services.local_bullets import (
        generate_generic_bullets,
        generate_language_specific_bullets,
    )

    # Use language-specific generator if available
    if analysis.language == "C/C++" and "c_cpp_summary" in analysis.language_analysis:
        summary = analysis.language_analysis["c_cpp_summary"]
        return generate_language_specific_bullets(summary, "C/C++", max_bullets)

    # Future languages will automatically work:
    # elif analysis.language == "Python" and "python_summary" in analysis.language_analysis:
    #     summary = analysis.language_analysis["python_summary"]
    #     return generate_language_specific_bullets(summary, "Python", max_bullets)

    # Fall back to generic local generation
    return generate_generic_bullets(analysis, max_bullets)


def _append_testing_bullet(bullets: list[str], analysis: ProjectAnalysis) -> list[str]:
    """Append the standardized testing bullet if available."""

    testing_bullet = build_testing_bullet(analysis)
    if not testing_bullet:
        return bullets

    updated = list(bullets)
    updated.append(testing_bullet)
    return updated


def build_testing_bullet(analysis: ProjectAnalysis) -> str | None:
    """Construct the mandatory testing bullet from aggregated metrics."""

    if analysis.test_case_count == 0 and analysis.test_file_count == 0:
        return None

    unit = analysis.unit_test_count
    integration = analysis.integration_test_count

    if unit > 0 and integration > 0:
        summary = f"Implemented {unit:,} unit and {integration:,} integration tests"
    elif unit > 0:
        summary = f"Implemented {unit:,} unit tests"
    elif integration > 0:
        summary = f"Implemented {integration:,} integration tests"
    elif analysis.test_case_count:
        summary = f"Implemented {analysis.test_case_count:,} automated tests"
    elif analysis.test_file_count:
        summary = f"Maintained {analysis.test_file_count:,} dedicated test files"
    else:
        return None
    language_fragment = _format_language_fragment(analysis.tests_by_language)
    if language_fragment:
        summary = f"{summary} across {language_fragment}"

    return f"{summary} to guard critical workflows and prevent regressions."


def _format_language_fragment(tests_by_language: dict[str, int]) -> str:
    """Return a readable fragment describing covered languages."""

    if not tests_by_language:
        return ""

    ordered = sorted(
        tests_by_language.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    languages = [name for name, count in ordered if count > 0 and name and name != "Unknown"]
    if not languages:
        languages = [name for name, _ in ordered if name and name != "Unknown"]

    if not languages:
        return ""

    if len(languages) == 1:
        return f"{languages[0]} modules"

    if len(languages) == 2:
        return f"{languages[0]} and {languages[1]} modules"

    return f"{languages[0]}, {languages[1]}, and {len(languages) - 2} other stacks"

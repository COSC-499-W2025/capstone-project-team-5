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
) -> tuple[list[str], str]:
    """Generate resume bullets with proper AI/local fallback.

    This is the main entry point for bullet generation. It:
    1. Runs complete project analysis (all analyzers)
    2. Tries AI generation if permitted
    3. Falls back to local generation if needed
    4. Returns bullets and source indicator

    Args:
        project_path: Path to project directory
        max_bullets: Maximum number of bullets to generate
        use_ai: Whether AI generation is allowed (consent)
        ai_available: Whether AI API is configured

    Returns:
        Tuple of (bullets list, source) where source is "AI" or "Local"
    """
    project_path = Path(project_path)

    # Step 1: Run complete analysis (always)
    analysis = analyze_project(project_path)

    # Step 2: Try AI first if allowed and available
    if use_ai and ai_available:
        ai_bullets = _try_ai_generation(analysis, max_bullets)
        if ai_bullets:
            return ai_bullets, "AI"

    # Step 3: Fall back to local generation
    local_bullets = _generate_local_bullets(analysis, max_bullets)
    return local_bullets, "Local"


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
    # Use language-specific generator if available
    if analysis.language == "C/C++" and "c_cpp_summary" in analysis.language_analysis:
        return _generate_cpp_local_bullets(analysis, max_bullets)

    # Future: elif analysis.language == "Python" and "python_summary" in analysis.language_analysis:
    #     return _generate_python_local_bullets(analysis, max_bullets)

    # Fall back to generic local generation
    return _generate_generic_local_bullets(analysis, max_bullets)


def _generate_cpp_local_bullets(analysis: ProjectAnalysis, max_bullets: int) -> list[str]:
    """Generate C/C++ specific local bullets using the enhanced analyzer.

    Args:
        analysis: Project analysis with C/C++ summary
        max_bullets: Maximum bullets to generate

    Returns:
        List of C/C++ specific resume bullets
    """
    try:
        from capstone_project_team_5.services.c_bullets import generate_c_bullets

        summary = analysis.language_analysis["c_cpp_summary"]
        return generate_c_bullets(summary, max_bullets=max_bullets)
    except (ImportError, KeyError):
        return _generate_generic_local_bullets(analysis, max_bullets)


def _generate_generic_local_bullets(analysis: ProjectAnalysis, max_bullets: int) -> list[str]:
    """Generate generic local bullets based on aggregated analysis.

    This is used when no language-specific generator is available.

    Args:
        analysis: Project analysis
        max_bullets: Maximum bullets to generate

    Returns:
        List of generic resume bullets
    """
    bullets = []

    # Determine technology stack
    tech_stack = (
        f"{analysis.language}/{analysis.framework}" if analysis.framework else analysis.language
    )

    # Opening bullet - project scope
    if analysis.lines_of_code > 0 and analysis.total_files > 0:
        bullets.append(
            f"Developed a {tech_stack} application with {analysis.lines_of_code:,} lines "
            f"of code across {analysis.total_files} files"
        )
    else:
        file_count = len(analysis.tools | analysis.practices)
        if file_count > 0:
            bullets.append(
                f"Built a {tech_stack} project with {file_count} identified components "
                f"and configuration files"
            )

    # OOP and architecture (if applicable)
    if analysis.oop_score > 0:
        oop_desc = []
        if analysis.class_count > 0:
            oop_desc.append(f"{analysis.class_count} classes")
        if analysis.function_count > 0:
            oop_desc.append(f"{analysis.function_count} functions")

        if oop_desc:
            bullets.append(f"Architected a modular design implementing {' and '.join(oop_desc)}")

    # OOP features
    if analysis.oop_features:
        features = ", ".join(sorted(analysis.oop_features))
        bullets.append(
            f"Applied object-oriented principles including {features} "
            f"for maintainable and extensible code"
        )

    # Design patterns
    if analysis.design_patterns:
        if len(analysis.design_patterns) == 1:
            pattern = list(analysis.design_patterns)[0]
            bullets.append(
                f"Implemented the {pattern} design pattern to solve architectural challenges"
            )
        else:
            patterns = ", ".join(sorted(analysis.design_patterns))
            bullets.append(
                f"Utilized multiple design patterns ({patterns}) for robust architecture"
            )

    # Data structures
    if analysis.data_structures:
        ds_list = sorted(analysis.data_structures)
        if len(ds_list) <= 2:
            ds_str = " and ".join(ds_list)
        else:
            ds_str = f"{', '.join(ds_list[:2])}, and {len(ds_list) - 2} others"

        bullets.append(f"Developed custom data structures ({ds_str}) optimized for performance")

    # Algorithms
    if analysis.algorithms:
        algo_types = ", ".join(sorted(analysis.algorithms))
        bullets.append(f"Implemented efficient algorithms for {algo_types} operations")

    # Technical features
    if analysis.technical_features:
        features = ", ".join(sorted(analysis.technical_features))
        bullets.append(f"Leveraged {features} for robust implementation")

    # Tools and practices
    if analysis.tools:
        tool_count = len(analysis.tools)
        if tool_count <= 3:
            tools_str = ", ".join(sorted(analysis.tools))
        else:
            tools_list = sorted(analysis.tools)
            tools_str = f"{', '.join(tools_list[:3])}, and {tool_count - 3} others"

        bullets.append(f"Utilized industry-standard tools including {tools_str}")

    # Development practices
    if analysis.practices:
        practices_str = ", ".join(sorted(analysis.practices))
        bullets.append(f"Followed best practices: {practices_str}")

    return bullets[:max_bullets]

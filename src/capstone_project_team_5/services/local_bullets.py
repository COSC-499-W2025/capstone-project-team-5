"""
Local bullet point generation without LLM.

This module provides logic-based bullet generation for projects
without requiring AI/LLM services. It uses static code analysis
to extract meaningful statistics and generate resume-style bullets.

Architecture for Adding New Language Analyzers
-----------------------------------------------
To add a new language analyzer (e.g., Python, JavaScript, Java):

1. Create your analyzer module (e.g., `python_analyzer.py`):
   - Define stats dataclasses (PythonFileStats, PythonProjectSummary)
   - Implement analyzer class with analyze_file() and analyze_project() methods
   - Add generate_summary_text() for formatted output

2. Create your bullet generator (e.g., `services/python_bullets.py`):
   - Implement generate_python_bullets(summary) -> list[str]
   - Implement generate_python_project_bullets(path) -> list[str]
   - Use natural, human-like language in bullets

3. Integrate with this module:
   Add a conditional in generate_local_bullets():
   ```python
   if language == "Python":
       from capstone_project_team_5.services.python_bullets import generate_python_project_bullets

       bullets.extend(generate_python_project_bullets(root)[:max_bullets])
       return bullets
   ```

4. Add tests (minimum 20 tests covering edge cases)

See c_analyzer.py and services/c_bullets.py as reference implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.services.c_bullets import (
    generate_c_bullets,
    generate_c_project_bullets,
)

if TYPE_CHECKING:
    from capstone_project_team_5.services.project_analysis import ProjectAnalysis


def _get_role_action_verb(user_role: str | None) -> str:
    """Get role-appropriate action verb for bullet points.

    Args:
        user_role: The detected user role (e.g., "Lead Developer", "Contributor")

    Returns:
        Action verb that matches the user's role
    """
    if not user_role:
        return "Developed"

    role_verbs = {
        "Solo Developer": "Independently developed",
        "Lead Developer": "Led development of",
        "Major Contributor": "Contributed significantly to",
        "Contributor": "Contributed to",
        "Minor Contributor": "Assisted in developing",
    }

    return role_verbs.get(user_role, "Developed")


def generate_local_bullets(project_root: Path | str, *, max_bullets: int = 6) -> list[str]:
    """Generate bullet points using local analysis (no LLM).

    This function analyzes a project directory and generates resume-style
    bullet points based on static code analysis. It works for various
    project types and falls back to generic metrics when specific
    analyzers are not available.

    Args:
        project_root: Path to the project root directory.
        max_bullets: Maximum number of bullets to generate (default: 6).

    Returns:
        List of bullet point strings suitable for a resume.
    """
    root = Path(project_root)
    bullets: list[str] = []

    # Detect project language and framework
    language, framework = identify_language_and_framework(root)

    # Use specialized analyzer for C/C++ projects
    if language == "C/C++":
        c_bullets = generate_c_project_bullets(root)
        bullets.extend(c_bullets[:max_bullets])
        return bullets

    # Use specialized analyzer for JavaScript/TypeScript projects
    if language == "JavaScript" or language == "TypeScript":
        from capstone_project_team_5.services.js_bullets import generate_js_project_bullets

        js_bullets = generate_js_project_bullets(root, max_bullets=max_bullets)
        bullets.extend(js_bullets)
        return bullets

    # For other languages, generate generic bullets based on metrics
    bullets = _generate_generic_bullets(root, language, framework)

    return bullets[:max_bullets]


def _generate_generic_bullets(
    project_root: Path, language: str, framework: str | None
) -> list[str]:
    """Generate generic bullets based on project metrics.

    Args:
        project_root: Path to the project root directory.
        language: Detected programming language.
        framework: Detected framework (if any).

    Returns:
        List of bullet point strings.
    """
    bullets: list[str] = []

    # Get contribution metrics
    contribution_metrics, _ = ContributionMetrics.get_project_contribution_metrics(project_root)
    duration, _ = ContributionMetrics.get_project_duration(project_root)

    # Calculate total contributions
    total_contributions = sum(contribution_metrics.values())
    if total_contributions == 0:
        return bullets

    # Primary project description - make it sound natural
    tech_stack = f"{language}/{framework}" if framework else language

    # Vary the opening based on project size
    if total_contributions > 50:
        bullets.append(
            f"Built a comprehensive {tech_stack} application featuring "
            f"{total_contributions} files across multiple components"
        )
    elif total_contributions > 20:
        bullets.append(
            f"Developed a {tech_stack} project with {total_contributions} files "
            f"spanning various aspects of the application"
        )
    else:
        bullets.append(
            f"Created a {tech_stack} application consisting of "
            f"{total_contributions} well-structured files"
        )

    # Duration bullet - only if meaningful
    if duration.days > 60:  # At least 2 months
        years = duration.days // 365
        months = (duration.days % 365) // 30

        if years > 0 and months > 3:
            bullets.append(
                f"Maintained and evolved the codebase over {years}+ years, "
                f"demonstrating long-term commitment"
            )
        elif years > 0:
            year_text = f"{years} year" + ("s" if years > 1 else "")
            bullets.append(f"Sustained development over {year_text} of active work")
        elif months > 6:
            bullets.append(
                f"Invested {months} months of continuous development to deliver a robust solution"
            )

    # Code implementation - be specific about what was built
    code_count = contribution_metrics.get("code", 0)
    if code_count > 10:
        bullets.append(
            f"Architected and implemented {code_count} source files "
            f"containing the application's core business logic"
        )
    elif code_count > 0:
        bullets.append(
            f"Wrote {code_count} source {'files' if code_count > 1 else 'file'} "
            f"implementing key features and functionality"
        )

    # Testing - emphasize quality
    test_count = contribution_metrics.get("test", 0)
    if test_count > 5:
        bullets.append(
            f"Established comprehensive test coverage with {test_count} test files "
            f"ensuring reliability and maintainability"
        )
    elif test_count > 0:
        bullets.append(
            f"Wrote {test_count} test {'suites' if test_count > 1 else 'suite'} "
            f"to validate functionality and prevent regressions"
        )

    # DevOps - show infrastructure knowledge
    devops_count = contribution_metrics.get("devops", 0)
    if devops_count > 3:
        bullets.append(
            f"Set up deployment infrastructure and CI/CD pipelines "
            f"across {devops_count} configuration files"
        )
    elif devops_count > 0:
        bullets.append(
            "Configured deployment and automation workflows to streamline the development process"
        )

    # Documentation - demonstrate communication skills
    doc_count = contribution_metrics.get("document", 0)
    if doc_count > 5:
        bullets.append(
            f"Authored extensive documentation across {doc_count} files "
            f"to facilitate team collaboration and onboarding"
        )
    elif doc_count > 0:
        bullets.append(
            "Created clear documentation to guide users and contributors through the project"
        )

    # Data handling - show data skills
    data_count = contribution_metrics.get("data", 0)
    if data_count > 0:
        bullets.append(
            f"Designed data structures and schemas across {data_count} "
            f"{'files' if data_count > 1 else 'file'} for efficient storage"
        )

    # Design - highlight UX awareness
    design_count = contribution_metrics.get("design", 0)
    if design_count > 0:
        bullets.append(
            f"Crafted {design_count} visual {'assets' if design_count > 1 else 'asset'} "
            f"to enhance user experience and interface design"
        )

    return bullets


def should_use_local_analysis(
    language: str, has_llm_consent: bool = True, llm_available: bool = True
) -> bool:
    """Determine if local analysis should be used instead of LLM.

    Args:
        language: Detected programming language.
        has_llm_consent: Whether user has consented to LLM usage.
        llm_available: Whether LLM service is available/configured.

    Returns:
        True if local analysis should be used.
    """
    # Use local analysis if LLM is not available or user hasn't consented
    if not llm_available or not has_llm_consent:
        return True

    # For C/C++, local analysis is often preferred as it's more accurate
    return language == "C/C++"


def generate_language_specific_bullets(
    summary: Any, language: str, max_bullets: int = 6
) -> list[str]:
    """Generate bullets from a language-specific summary object.

    This is a COMMON METHOD that routes to language-specific generators,
    making it easy to add new languages without modifying callers.

    Args:
        summary: Language-specific summary object (e.g., CProjectSummary)
        language: Programming language (e.g., "C/C++", "Python", "Java")
        max_bullets: Maximum number of bullets to generate

    Returns:
        List of professionally-written resume bullets

    Example:
        >>> from capstone_project_team_5.c_analyzer import CProjectSummary
        >>> summary = CProjectSummary(...)
        >>> bullets = generate_language_specific_bullets(summary, "C/C++", 6)
    """
    if language == "C/C++":
        return generate_c_bullets(summary, max_bullets=max_bullets)
    elif language == "JavaScript" or language == "TypeScript":
        from capstone_project_team_5.services.js_bullets import generate_js_bullets

        return generate_js_bullets(summary, max_bullets=max_bullets)
    # Future languages - just add new elif blocks:
    # elif language == "Python":
    #     from capstone_project_team_5.services.python_bullets import generate_python_bullets
    #     return generate_python_bullets(summary, max_bullets=max_bullets)
    # elif language == "Java":
    #     from capstone_project_team_5.services.java_bullets import generate_java_bullets
    #     return generate_java_bullets(summary, max_bullets=max_bullets)
    else:
        # No language-specific generator available
        return []


def generate_generic_bullets(analysis: ProjectAnalysis, max_bullets: int = 6) -> list[str]:
    """Generate generic bullets from ProjectAnalysis (no language-specific data).

    This is used as a fallback when no language-specific analyzer is available.

    Args:
        analysis: ProjectAnalysis with aggregated data
        max_bullets: Maximum bullets to generate

    Returns:
        List of generic resume bullets
    """
    bullets = []

    # Get role-aware action verbs
    action_verb = _get_role_action_verb(analysis.user_role)

    # Determine technology stack
    tech_stack = (
        f"{analysis.language}/{analysis.framework}" if analysis.framework else analysis.language
    )

    # Opening bullet - project scope (role-aware)
    if analysis.lines_of_code > 0 and analysis.total_files > 0:
        bullets.append(
            f"{action_verb} a {tech_stack} application with {analysis.lines_of_code:,} lines "
            f"of code across {analysis.total_files} files"
        )
    else:
        file_count = len(analysis.tools | analysis.practices)
        if file_count > 0:
            bullets.append(
                f"{action_verb} a {tech_stack} project with {file_count} identified components "
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

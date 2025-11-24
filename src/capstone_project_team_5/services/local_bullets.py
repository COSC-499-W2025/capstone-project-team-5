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

from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.services.c_bullets import generate_c_project_bullets


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

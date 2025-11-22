"""
C/C++ specific bullet point generation.

This module generates resume-style bullet points from C/C++ file analysis.
"""

from __future__ import annotations

from pathlib import Path

from capstone_project_team_5.c_analyzer import CFileAnalyzer, CProjectSummary, analyze_c_files


def generate_c_bullets(summary: CProjectSummary, *, max_bullets: int = 6) -> list[str]:
    """Generate resume-style bullet points from C/C++ analysis.

    Args:
        summary: CProjectSummary from analyzing C/C++ files.
        max_bullets: Maximum number of bullets to generate.

    Returns:
        List of bullet point strings suitable for a resume.
    """
    if summary.total_files == 0:
        return []

    bullets = []

    # Opening bullet - adapt to project type
    if summary.has_main:
        bullets.append(
            f"Built a C/C++ application with {summary.total_lines_of_code:,} lines of code "
            f"across {summary.total_files} files, demonstrating proficiency in systems programming"
        )
    else:
        bullets.append(
            f"Developed a C/C++ library containing {summary.total_functions} functions "
            f"across {summary.total_lines_of_code:,} lines of well-structured code"
        )

    # Architecture - highlight design skills
    if summary.total_structs > 0 or summary.total_classes > 0:
        structures = []
        if summary.total_structs > 0:
            structures.append(f"{summary.total_structs} data structures")
        if summary.total_classes > 0:
            structures.append(f"{summary.total_classes} classes")

        bullets.append(
            f"Architected a modular design using {' and '.join(structures)}, "
            f"implementing {summary.total_functions} well-defined functions"
        )

    # Memory management - critical for C/C++
    if summary.uses_memory_management:
        bullets.append(
            "Implemented efficient memory management with careful allocation and cleanup, "
            "preventing memory leaks and ensuring optimal resource usage"
        )

    # Pointer usage - shows advanced understanding
    if summary.uses_pointers and not summary.uses_memory_management:
        bullets.append(
            "Leveraged pointer operations and memory addressing "
            "for performance-critical data manipulation"
        )

    # Concurrency - valuable skill
    if summary.uses_concurrency:
        bullets.append(
            "Built multi-threaded functionality with proper synchronization, "
            "enabling concurrent processing for improved performance"
        )

    # Error handling - shows production-ready code
    if summary.uses_error_handling:
        bullets.append(
            "Implemented robust error handling throughout the codebase "
            "to ensure stability and graceful failure recovery"
        )

    # Library usage - demonstrates ecosystem knowledge
    if summary.libraries_used:
        lib_names = sorted(summary.libraries_used)
        if len(lib_names) == 1:
            lib_str = lib_names[0]
        elif len(lib_names) == 2:
            lib_str = f"{lib_names[0]} and {lib_names[1]}"
        elif len(lib_names) <= 4:
            lib_str = ", ".join(lib_names[:-1]) + f", and {lib_names[-1]}"
        else:
            lib_str = f"{', '.join(lib_names[:3])}, and {len(lib_names) - 3} other libraries"

        bullets.append(f"Integrated external libraries including {lib_str} to extend functionality")

    # Complexity handling - shows problem-solving
    if summary.avg_complexity > 5:
        bullets.append(
            f"Managed algorithmic complexity (avg score: {summary.avg_complexity:.1f}) "
            f"with clean control flow and maintainable logic"
        )

    return bullets[:max_bullets]


def generate_c_project_bullets(project_root: Path | str, *, max_bullets: int = 6) -> list[str]:
    """Generate resume bullet points for a C/C++ project directory.

    Args:
        project_root: Path to the project root directory.
        max_bullets: Maximum number of bullets to generate.

    Returns:
        List of bullet point strings.
    """
    summary = CFileAnalyzer.analyze_project(project_root)
    return generate_c_bullets(summary, max_bullets=max_bullets)


def generate_bullets_from_files(
    files: list[Path], root: Path | None = None, *, max_bullets: int = 6
) -> list[str]:
    """Generate resume bullets from a pre-filtered list of C/C++ files.

    Args:
        files: List of C/C++ file paths (pre-validated).
        root: Optional root directory for relative path calculation.
        max_bullets: Maximum number of bullets to generate.

    Returns:
        List of bullet point strings.
    """
    summary = analyze_c_files(files, root)
    return generate_c_bullets(summary, max_bullets=max_bullets)

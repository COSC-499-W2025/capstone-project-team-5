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
        if summary.total_functions > 0:
            bullets.append(
                f"Developed a C/C++ library containing {summary.total_functions} functions "
                f"across {summary.total_lines_of_code:,} lines of well-structured code"
            )
        else:
            bullets.append(
                f"Developed a C/C++ library with {summary.total_lines_of_code:,} lines "
                f"of well-structured code across {summary.total_files} files"
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

    # OOP Principles - shows advanced C++ knowledge
    if summary.uses_inheritance or summary.uses_polymorphism:
        oop_features = []
        if summary.uses_inheritance:
            oop_features.append("inheritance")
        if summary.uses_polymorphism:
            oop_features.append("polymorphism with virtual functions")

        bullets.append(
            f"Applied object-oriented principles including {' and '.join(oop_features)}, "
            f"creating maintainable and extensible class hierarchies"
        )

    # Design Patterns - demonstrates software engineering maturity
    if summary.design_patterns:
        patterns = sorted(summary.design_patterns)
        if len(patterns) == 1:
            pattern_str = f"the {patterns[0]} pattern"
        elif len(patterns) == 2:
            pattern_str = f"{patterns[0]} and {patterns[1]} patterns"
        else:
            pattern_str = f"{', '.join(patterns[:-1])}, and {patterns[-1]} patterns"

        bullets.append(
            f"Implemented industry-standard design patterns ({pattern_str}) "
            f"to solve common architectural challenges"
        )

    # Data Structures - shows algorithmic thinking
    if summary.data_structures:
        ds_list = sorted(summary.data_structures)
        if len(ds_list) == 1:
            ds_str = ds_list[0]
        elif len(ds_list) == 2:
            ds_str = f"{ds_list[0]} and {ds_list[1]}"
        else:
            ds_str = f"{', '.join(ds_list[:2])}, and {len(ds_list) - 2} other structures"

        bullets.append(
            f"Developed custom data structures ({ds_str}) "
            f"optimized for specific performance requirements"
        )

    # Algorithms - demonstrates problem-solving skills
    if summary.algorithms_used:
        algo_types = sorted(summary.algorithms_used)
        algo_str = ", ".join(a.replace("_", " ") for a in algo_types)

        bullets.append(
            f"Implemented efficient algorithms for {algo_str}, "
            f"demonstrating strong computational thinking and optimization skills"
        )

    # Modern C++ Features - shows up-to-date knowledge
    if summary.uses_modern_cpp or summary.uses_lambda or summary.uses_templates:
        modern_features = []
        if summary.uses_lambda:
            modern_features.append("lambda expressions")
        if summary.uses_templates:
            modern_features.append("generic programming with templates")
        if summary.uses_modern_cpp:
            modern_features.append("modern C++ idioms")

        bullets.append(
            f"Leveraged {', '.join(modern_features)} to write expressive, "
            f"type-safe, and performant code following C++11/14/17 standards"
        )

    # Complexity handling - shows problem-solving
    if summary.avg_complexity > 5 and len(bullets) < max_bullets:
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

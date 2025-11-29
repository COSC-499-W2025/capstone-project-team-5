"""
Unified project analysis system.

This module aggregates analysis from multiple sources:
- Language/framework detection
- Skill detection (tools & practices)
- Language-specific analyzers (C/C++, Python, etc.)
- Contribution metrics
- Collaboration data

Provides a single source of truth for all project analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.skill_detection import extract_project_tools_practices


@dataclass
class ProjectAnalysis:
    """Aggregated analysis of a project from all sources.

    This is the unified data structure that combines:
    - Language/framework info
    - Tools and practices
    - Language-specific features (OOP, patterns, algorithms, etc.)
    - Any other analysis data

    Both AI and local bullet generators use this as input.
    """

    # Basic project info
    project_path: Path
    language: str
    framework: str | None = None

    # Skill detection (always available)
    tools: set[str] = field(default_factory=set)
    practices: set[str] = field(default_factory=set)

    # Language-specific analysis (optional, depends on language)
    language_analysis: dict[str, any] = field(default_factory=dict)

    # Aggregated technical features (from language analyzers)
    technical_features: set[str] = field(default_factory=set)
    oop_features: set[str] = field(default_factory=set)
    design_patterns: set[str] = field(default_factory=set)
    data_structures: set[str] = field(default_factory=set)
    algorithms: set[str] = field(default_factory=set)

    # Code metrics (aggregated from language analyzers)
    total_files: int = 0
    lines_of_code: int = 0
    function_count: int = 0
    class_count: int = 0

    # Scores/ratings
    oop_score: float = 0.0  # 0-10 scale
    complexity_score: float = 0.0


def analyze_project(project_path: Path) -> ProjectAnalysis:
    """Analyze a project using all available analyzers.

    This is the main entry point for project analysis. It:
    1. Detects language/framework
    2. Runs skill detection
    3. Runs language-specific analyzer if available
    4. Aggregates all results into a single ProjectAnalysis object

    Args:
        project_path: Path to the project directory

    Returns:
        ProjectAnalysis with aggregated data from all sources
    """
    project_path = Path(project_path)

    # Step 1: Detect language and framework
    language, framework = identify_language_and_framework(project_path)

    # Step 2: Skill detection (always runs)
    skills_map = extract_project_tools_practices(project_path)
    tools = skills_map.get("tools", set())
    practices = skills_map.get("practices", set())

    # Step 3: Initialize analysis object
    analysis = ProjectAnalysis(
        project_path=project_path,
        language=language,
        framework=framework,
        tools=tools,
        practices=practices,
    )

    # Step 4: Run language-specific analyzer if available
    if language == "C/C++":
        _analyze_cpp_project(analysis)
    elif language == "Java":
        _analyze_java_project(analysis)
    elif language == "Python":
        _analyze_python_project(analysis)
    # Future: elif language == "JavaScript":
    #     _analyze_javascript_project(analysis)

    return analysis


def _analyze_cpp_project(analysis: ProjectAnalysis) -> None:
    """Run C/C++ specific analysis and update the ProjectAnalysis object.

    Args:
        analysis: ProjectAnalysis object to update with C/C++ specific data
    """
    try:
        from capstone_project_team_5.c_analyzer import analyze_c_project

        summary = analyze_c_project(analysis.project_path)

        # Store raw summary for C-specific bullet generation
        analysis.language_analysis["c_cpp_summary"] = summary

        # Update aggregated metrics
        analysis.total_files = summary.total_files
        analysis.lines_of_code = summary.total_lines_of_code
        analysis.function_count = summary.total_functions
        analysis.class_count = summary.total_classes
        analysis.oop_score = summary.oop_score
        analysis.complexity_score = summary.avg_complexity

        # Aggregate technical features
        if summary.uses_pointers:
            analysis.technical_features.add("Pointer Operations")
        if summary.uses_memory_management:
            analysis.technical_features.add("Manual Memory Management")
        if summary.uses_concurrency:
            analysis.technical_features.add("Multi-threading")
        if summary.uses_error_handling:
            analysis.technical_features.add("Error Handling")

        # Aggregate OOP features
        if summary.uses_inheritance:
            analysis.oop_features.add("Inheritance")
        if summary.uses_polymorphism:
            analysis.oop_features.add("Polymorphism")
        if summary.uses_templates:
            analysis.oop_features.add("Generic Programming")
        if summary.uses_lambda:
            analysis.oop_features.add("Lambda Expressions")
        if summary.uses_modern_cpp:
            analysis.oop_features.add("Modern C++")

        # Copy design patterns, data structures, algorithms
        analysis.design_patterns.update(summary.design_patterns)
        analysis.data_structures.update(summary.data_structures)
        analysis.algorithms.update(summary.algorithms_used)

    except ImportError:
        # C analyzer not available, skip
        pass


def _analyze_java_project(analysis: ProjectAnalysis) -> None:
    """Run Java specific analysis and update the ProjectAnalysis object.

    Args:
        analysis: ProjectAnalysis object to update with Java specific data
    """
    try:
        from capstone_project_team_5.java_analyzer import analyze_java_project

        result = analyze_java_project(analysis.project_path)

        # Check for errors from analyzer
        if "error" in result:
            return

        # Store raw result for Java-specific bullet generation
        analysis.language_analysis["java_result"] = result

        # Update aggregated metrics
        analysis.total_files = result.get("total_files", 0)
        analysis.lines_of_code = result.get("lines_of_code", 0)
        analysis.function_count = result.get("methods_count", 0)
        analysis.class_count = result.get("classes_count", 0)

        # Calculate OOP score based on principles detected
        oop_principles = result.get("oop_principles", {})
        oop_score = sum(oop_principles.values()) * 2.5  # 0-10 scale (4 principles * 2.5)
        analysis.oop_score = oop_score

        # Aggregate technical features
        if result.get("uses_recursion"):
            analysis.algorithms.add("Recursion")
        if result.get("uses_bfs"):
            analysis.algorithms.add("BFS")
        if result.get("uses_dfs"):
            analysis.algorithms.add("DFS")

        # Aggregate OOP features
        if oop_principles.get("Encapsulation"):
            analysis.oop_features.add("Encapsulation")
        if oop_principles.get("Inheritance"):
            analysis.oop_features.add("Inheritance")
        if oop_principles.get("Polymorphism"):
            analysis.oop_features.add("Polymorphism")
        if oop_principles.get("Abstraction"):
            analysis.oop_features.add("Abstraction")

        # Copy design patterns and data structures
        analysis.design_patterns.update(result.get("coding_patterns", []))
        analysis.data_structures.update(result.get("data_structures", []))

    except ImportError:
        # Java analyzer not available, skip
        pass


# Future: Add more language analyzers following the same pattern
def _analyze_python_project(analysis: ProjectAnalysis) -> None:
    """Run Python specific analysis and update the ProjectAnalysis object.

    Args:
        analysis: ProjectAnalysis object to update with Python specific data

    TODO: Document which fields get populated (metrics, oop_score, features, etc.)
    """
    try:
        from capstone_project_team_5.python_analyzer import analyze_python_project

        result = analyze_python_project(analysis.project_path)

        # Check for errors from analyzer
        if "error" in result:
            return

        # Store raw result for Python-specific bullet generation
        analysis.language_analysis["python_result"] = result

        # Update aggregated metrics
        analysis.total_files = result.get("total_files", 0)
        analysis.lines_of_code = result.get("lines_of_code", 0)
        analysis.function_count = result.get("methods_count", 0)
        analysis.class_count = result.get("classes_count", 0)
        # TODO: Add complexity_score calculation (currently always 0 for Python)

        # Calculate OOP score based on principles detected
        oop_principles = result.get("oop_principles", {})
        oop_score = sum(oop_principles.values()) * 2.5  # 0-10 scale (4 principles * 2.5)
        analysis.oop_score = oop_score

        # Aggregate OOP features
        if oop_principles.get("Encapsulation"):
            analysis.oop_features.add("Encapsulation")
        if oop_principles.get("Inheritance"):
            analysis.oop_features.add("Inheritance")
        if oop_principles.get("Polymorphism"):
            analysis.oop_features.add("Polymorphism")
        if oop_principles.get("Abstraction"):
            analysis.oop_features.add("Abstraction")

        # Aggregate technical features from detected features
        features = result.get("features", [])
        analysis.technical_features.update(features)

        # TODO: Map tech_stack (frameworks, database, testing, tooling) to technical_features
        # TODO: Map integrations (http, aws, cache, data) to technical_features or new field

        # Copy design patterns, data structures, and algorithms
        analysis.design_patterns.update(result.get("design_patterns", []))
        analysis.data_structures.update(result.get("data_structures", []))
        analysis.algorithms.update(result.get("algorithms", []))

    except ImportError:
        pass

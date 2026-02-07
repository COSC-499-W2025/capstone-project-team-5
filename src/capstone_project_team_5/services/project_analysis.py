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
from typing import TYPE_CHECKING

from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.services.test_analysis import analyze_tests
from capstone_project_team_5.skill_detection import extract_project_tools_practices

if TYPE_CHECKING:
    from capstone_project_team_5.consent_tool import ConsentTool


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

    # Testing metrics
    test_file_count: int = 0
    test_case_count: int = 0
    unit_test_count: int = 0
    integration_test_count: int = 0
    test_frameworks: set[str] = field(default_factory=set)
    tests_by_language: dict[str, int] = field(default_factory=dict)
    tests_by_framework: dict[str, int] = field(default_factory=dict)

    # User role information (detected from Git contributions)
    user_role: str | None = None
    user_contribution_percentage: float | None = None
    role_justification: str | None = None


def analyze_project(project_path: Path, consent_tool: ConsentTool | None = None) -> ProjectAnalysis:
    """Analyze a project using all available analyzers.

    This is the main entry point for project analysis. It:
    1. Detects language/framework
    2. Runs skill detection
    3. Runs language-specific analyzer if available
    4. Aggregates all results into a single ProjectAnalysis object

    Args:
        project_path: Path to the project directory
        consent_tool: Optional ConsentTool for checking LLM permissions.

    Returns:
        ProjectAnalysis with aggregated data from all sources
    """
    project_path = Path(project_path)

    # Step 1: Detect language and framework
    language, framework = identify_language_and_framework(project_path)

    # Step 2: Skill detection (always runs)
    skills_map = extract_project_tools_practices(project_path, consent_tool)
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
    elif language == "JavaScript" or language == "TypeScript":
        _analyze_js_project(analysis)

    _populate_test_metrics(analysis)

    return analysis


def _populate_test_metrics(analysis: ProjectAnalysis) -> None:
    """Populate aggregated testing metrics for the project."""

    test_result = analyze_tests(analysis.project_path)
    analysis.test_file_count = test_result.test_file_count
    analysis.test_case_count = test_result.test_case_count
    analysis.unit_test_count = test_result.unit_test_count
    analysis.integration_test_count = test_result.integration_test_count
    analysis.tests_by_language = dict(test_result.tests_by_language)
    analysis.tests_by_framework = dict(test_result.tests_by_framework)
    analysis.test_frameworks.update(test_result.frameworks)
    analysis.language_analysis["test_files"] = [str(item.path) for item in test_result.files]


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

        testing_stack = result.get("tech_stack", {}).get("testing", [])
        analysis.test_frameworks.update(testing_stack)

    except ImportError:
        # Java analyzer not available, skip
        pass


# Future: Add more language analyzers following the same pattern
def _analyze_python_project(analysis: ProjectAnalysis) -> None:
    """Run Python specific analysis and update the ProjectAnalysis object.

    Args:
        analysis: ProjectAnalysis object to update with Python specific data.

    Populates:
    - language_analysis["python_result"] with the raw analyzer result.
    - total_files, lines_of_code, function_count, class_count.
    - oop_score and oop_features based on detected OOP principles.
    - complexity_score derived from average function complexity (0-10 scale).
    - technical_features augmented from Python features, tech_stack, and integrations.
    - design_patterns, data_structures, and algorithms from the analyzer.
    - test_frameworks from the Python tech_stack.
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
        complexity_score = float(result.get("complexity_score", 0.0))
        analysis.complexity_score = complexity_score

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

        # Map tech_stack (frameworks, database, testing, tooling) to technical_features
        tech_stack = result.get("tech_stack", {})
        for category, items in tech_stack.items():
            analysis.technical_features.update(items)
            if category == "database" and items:
                analysis.technical_features.add("Database Integration")
            if category == "testing" and items:
                analysis.technical_features.add("Automated Testing")
            if category == "frameworks" and items:
                analysis.technical_features.add("Web Framework")

        # Map integrations (http, aws, cache, data) to technical_features
        integrations = result.get("integrations", {})
        if "http" in integrations:
            analysis.technical_features.add("HTTP API Integration")
        if "aws" in integrations:
            analysis.technical_features.add("Cloud Integration (AWS)")
        if "cache" in integrations:
            analysis.technical_features.add("Caching & Messaging")
        if "data" in integrations:
            analysis.technical_features.add("Data Processing")

        # Copy design patterns, data structures, and algorithms
        analysis.design_patterns.update(result.get("design_patterns", []))
        analysis.data_structures.update(result.get("data_structures", []))
        analysis.algorithms.update(result.get("algorithms", []))

        testing_stack = result.get("tech_stack", {}).get("testing", [])
        analysis.test_frameworks.update(testing_stack)

    except ImportError:
        pass


def _analyze_js_project(analysis: ProjectAnalysis) -> None:
    """Run JavaScript/TypeScript specific analysis and update the ProjectAnalysis object.

    Args:
        analysis: ProjectAnalysis object to update with JS/TS specific data
    """
    try:
        from capstone_project_team_5.js_code_analyzer import analyze_js_project

        summary = analyze_js_project(analysis.project_path, analysis.language, analysis.framework)

        analysis.language_analysis["js_ts_summary"] = summary

        analysis.total_files = summary.total_files
        analysis.lines_of_code = summary.total_lines_of_code

        for _category, items in summary.tech_stack.items():
            analysis.tools.update(items)

        analysis.practices.update(summary.features)

        if summary.tech_stack.get("backend"):
            analysis.technical_features.add("Backend Development")
            analysis.technical_features.add("API Development")

        if summary.tech_stack.get("database"):
            analysis.technical_features.add("Database Integration")

        if summary.tech_stack.get("testing"):
            analysis.technical_features.add("Automated Testing")

        if summary.uses_typescript:
            analysis.technical_features.add("TypeScript")

        if summary.tech_stack.get("frontend"):
            analysis.technical_features.add("Frontend Development")

        if summary.uses_react:
            analysis.oop_features.add("Component-Based Architecture")
            analysis.oop_features.add("React Hooks")

        if summary.uses_nodejs:
            analysis.oop_features.add("Event-Driven Architecture")

        analysis.design_patterns.update(summary.design_patterns)

        if summary.integrations:
            analysis.language_analysis["js_ts_integrations"] = summary.integrations

        if summary.total_classes > 0:
            analysis.class_count = summary.total_classes
            analysis.oop_features.update(summary.oop_features)

        analysis.function_count = summary.total_functions
        analysis.data_structures.update(summary.data_structures)
        analysis.algorithms.update(summary.algorithms_used)

        analysis.language_analysis["ast_metrics"] = {
            "function_count": summary.total_functions,
            "class_count": summary.total_classes,
            "import_count": summary.total_imports,
            "export_count": summary.total_exports,
            "avg_complexity": summary.avg_function_complexity,
            "max_complexity": summary.max_function_complexity,
            "custom_hooks": summary.custom_hooks_count,
        }

        if summary.uses_async_await:
            analysis.technical_features.add("Asynchronous Programming")

        if summary.custom_hooks_count > 0:
            analysis.technical_features.add("Custom React Hooks")

        if summary.total_imports > 20:
            analysis.technical_features.add("Modular Architecture")

        if summary.total_classes > 0:
            oop_feature_count = len(summary.oop_features)
            class_ratio = min(1.0, summary.total_classes / max(1, summary.total_functions))
            analysis.oop_score = min(10.0, (oop_feature_count * 2) + (class_ratio * 4))

        if summary.max_function_complexity > 10:
            analysis.technical_features.add("Complex Business Logic")
        elif summary.avg_function_complexity < 3:
            analysis.practices.add("Simple, Maintainable Code")

        if "Recursion" in summary.algorithms_used:
            analysis.technical_features.add("Recursive Algorithms")

        if "Memoization" in summary.algorithms_used:
            analysis.technical_features.add("Performance Optimization")

        if summary.avg_function_complexity > 0:
            analysis.complexity_score = min(10.0, summary.avg_function_complexity)

    except ImportError:
        # JS analyzer not available, skip
        pass

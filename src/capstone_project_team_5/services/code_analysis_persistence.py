"""
Service for persisting code analysis results to the database.

This module provides language-agnostic functions to save analysis results
from any language analyzer (C/C++, Python, Java, JavaScript, etc.) to the
code_analyses table.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from capstone_project_team_5.services.skill_persistence import save_skills_to_db

if TYPE_CHECKING:
    from capstone_project_team_5.services.project_analysis import ProjectAnalysis


def save_code_analysis_to_db(
    project_name: str,
    project_rel_path: str,
    analysis: ProjectAnalysis,
    username: str | None = None,
) -> None:
    """Save code analysis results to the database (language-agnostic).

    This function handles analysis from ANY programming language:
    - C/C++: Uses c_cpp_summary from language_analysis
    - Python: Will use python_summary from language_analysis (future)
    - Java: Will use java_summary from language_analysis (future)
    - JavaScript: Will use js_summary from language_analysis (future)
    - Generic: Falls back to aggregated ProjectAnalysis data

    The function:
    1. Finds the project in the database
    2. Checks if analysis already exists (to avoid duplicates)
    3. Prepares metrics JSON based on language-specific data
    4. Saves to code_analyses table

    Args:
        project_name: Name of the project
        project_rel_path: Relative path of the project
        analysis: ProjectAnalysis containing language-specific analysis data

    Note:
        Silently returns if:
        - Project not found in database (upload not yet complete)
        - Analysis already exists (avoid duplicates)
        - Any database error occurs (don't fail CLI)
    """
    try:
        from capstone_project_team_5.data.db import get_session
        from capstone_project_team_5.data.models import (
            CodeAnalysis,
            Project,
            User,
            UserCodeAnalysis,
        )

        # Find the project in the database
        with get_session() as session:
            project = (
                session.query(Project)
                .filter(Project.name == project_name, Project.rel_path == project_rel_path)
                .first()
            )

            if not project:
                return  # Project not yet in DB, skip

            # Update project with role data if available
            if analysis.user_role is not None:
                project.user_role = analysis.user_role
            if analysis.user_contribution_percentage is not None:
                project.user_contribution_percentage = analysis.user_contribution_percentage
            if analysis.role_justification is not None:
                project.role_justification = analysis.role_justification

            if analysis.user_role_types is not None:
                project.user_role_types = analysis.user_role_types

            # Prepare metrics and summary based on language
            metrics_json, summary_text = _prepare_language_specific_data(analysis)

            if not metrics_json:
                # No language-specific data available, use generic aggregated data
                metrics_json, summary_text = _prepare_generic_data(analysis)

            # Create and save analysis
            code_analysis = CodeAnalysis(
                project_id=project.id,
                language=analysis.language,
                analysis_type="local",
                metrics_json=json.dumps(metrics_json),
                summary_text=summary_text,
            )
            session.add(code_analysis)
            session.flush()  # ensure code_analysis.id is populated

            if username is not None:
                user = session.query(User).filter(User.username == username.strip()).first()
                if user is not None:
                    session.add(UserCodeAnalysis(user_id=user.id, analysis_id=code_analysis.id))

            # Save skills (tools and practices) to Skill and ProjectSkill tables
            save_skills_to_db(session, project.id, analysis.tools, analysis.practices)

            session.commit()

    except Exception:
        # Don't fail the CLI if database save fails
        # This could be due to database not being initialized, connection issues, etc.
        pass


def _prepare_language_specific_data(
    analysis: ProjectAnalysis,
) -> tuple[dict[str, any] | None, str | None]:
    """Extract language-specific metrics and summary from ProjectAnalysis.

    This function checks for language-specific analysis data and formats it
    appropriately for database storage.

    Args:
        analysis: ProjectAnalysis with potential language-specific data

    Returns:
        Tuple of (metrics_dict, summary_text) or (None, None) if no specific data
    """
    language = analysis.language

    # C/C++ specific analysis
    if language == "C/C++" and "c_cpp_summary" in analysis.language_analysis:
        return _prepare_cpp_data(analysis.language_analysis["c_cpp_summary"])

    # Python specific analysis (future)
    # if language == "Python" and "python_summary" in analysis.language_analysis:
    #     return _prepare_python_data(analysis.language_analysis["python_summary"])

    # Java specific analysis (future)
    # if language == "Java" and "java_summary" in analysis.language_analysis:
    #     return _prepare_java_data(analysis.language_analysis["java_summary"])

    # JavaScript specific analysis (future)
    # if language == "JavaScript" and "js_summary" in analysis.language_analysis:
    #     return _prepare_javascript_data(analysis.language_analysis["js_summary"])

    return None, None


def _prepare_cpp_data(summary: any) -> tuple[dict[str, any], str]:
    """Prepare C/C++ specific metrics for database storage.

    Args:
        summary: C++ project summary from c_analyzer

    Returns:
        Tuple of (metrics_dict, summary_text)
    """
    from capstone_project_team_5.c_analyzer import generate_summary_text

    metrics = {
        "total_files": summary.total_files,
        "total_lines_of_code": summary.total_lines_of_code,
        "total_functions": summary.total_functions,
        "total_classes": summary.total_classes,
        "total_structs": summary.total_structs,
        "oop_score": summary.oop_score,
        "avg_complexity": summary.avg_complexity,
        "uses_inheritance": summary.uses_inheritance,
        "uses_polymorphism": summary.uses_polymorphism,
        "uses_templates": summary.uses_templates,
        "uses_lambda": summary.uses_lambda,
        "uses_modern_cpp": summary.uses_modern_cpp,
        "uses_pointers": summary.uses_pointers,
        "uses_memory_management": summary.uses_memory_management,
        "uses_concurrency": summary.uses_concurrency,
        "uses_error_handling": summary.uses_error_handling,
        "design_patterns": list(summary.design_patterns),
        "data_structures": list(summary.data_structures),
        "algorithms": list(summary.algorithms_used),
    }

    summary_text = generate_summary_text(summary)

    return metrics, summary_text


def _prepare_generic_data(analysis: ProjectAnalysis) -> tuple[dict[str, any], str]:
    """Prepare generic metrics from aggregated ProjectAnalysis data.

    This is used when no language-specific analyzer data is available.
    It uses the aggregated fields from ProjectAnalysis.

    Args:
        analysis: ProjectAnalysis with aggregated data

    Returns:
        Tuple of (metrics_dict, summary_text)
    """
    metrics = {
        "language": analysis.language,
        "framework": analysis.framework,
        "total_files": analysis.total_files,
        "lines_of_code": analysis.lines_of_code,
        "function_count": analysis.function_count,
        "class_count": analysis.class_count,
        "oop_score": analysis.oop_score,
        "complexity_score": analysis.complexity_score,
        "tools": list(analysis.tools),
        "practices": list(analysis.practices),
        "technical_features": list(analysis.technical_features),
        "oop_features": list(analysis.oop_features),
        "design_patterns": list(analysis.design_patterns),
        "data_structures": list(analysis.data_structures),
        "algorithms": list(analysis.algorithms),
        "test_file_count": analysis.test_file_count,
        "test_case_count": analysis.test_case_count,
        "unit_test_count": analysis.unit_test_count,
        "integration_test_count": analysis.integration_test_count,
        "test_frameworks": sorted(analysis.test_frameworks),
        "tests_by_language": analysis.tests_by_language,
        "tests_by_framework": analysis.tests_by_framework,
    }

    # Generate a simple summary
    summary_parts = []
    if analysis.lines_of_code > 0:
        summary_parts.append(f"{analysis.language} project with {analysis.lines_of_code} LOC")
    else:
        summary_parts.append(f"{analysis.language} project")

    if analysis.framework:
        summary_parts.append(f"using {analysis.framework}")

    if analysis.tools:
        tools_str = ", ".join(sorted(list(analysis.tools)[:3]))
        summary_parts.append(f"Tools: {tools_str}")

    summary_text = ". ".join(summary_parts)

    return metrics, summary_text


def delete_code_analysis(analysis_id: int) -> bool:
    """Delete a specific code analysis by ID.

    This removes only the code analysis record, not the underlying
    project data.

    Args:
        analysis_id: Primary key of the code analysis to delete.

    Returns:
        bool: True if the analysis was deleted, False if it didn't exist.

    Note:
        Silently returns False if any database error occurs.
    """
    try:
        from capstone_project_team_5.data.db import get_session
        from capstone_project_team_5.data.models import CodeAnalysis

        with get_session() as session:
            result = (
                session.query(CodeAnalysis)
                .filter(CodeAnalysis.id == analysis_id)
                .delete(synchronize_session=False)
            )
            session.commit()
            return result > 0
    except Exception:
        return False


def delete_code_analyses_by_project(project_id: int) -> int:
    """Delete all code analyses for a specific project.

    This removes all code analysis records associated with a project,
    but preserves the project data itself.

    Args:
        project_id: ID of the project whose code analyses should be deleted.

    Returns:
        int: The number of code analyses deleted.

    Note:
        Silently returns 0 if any database error occurs.
    """
    try:
        from capstone_project_team_5.data.db import get_session
        from capstone_project_team_5.data.models import CodeAnalysis

        with get_session() as session:
            count = (
                session.query(CodeAnalysis)
                .filter(CodeAnalysis.project_id == project_id)
                .delete(synchronize_session=False)
            )
            session.commit()
            return count
    except Exception:
        return 0


# Future: Add more language-specific data preparation functions
# def _prepare_python_data(summary: any) -> tuple[dict[str, any], str]:
#     """Prepare Python specific metrics for database storage."""
#     pass
#
# def _prepare_java_data(summary: any) -> tuple[dict[str, any], str]:
#     """Prepare Java specific metrics for database storage."""
#     pass
#
# def _prepare_javascript_data(summary: any) -> tuple[dict[str, any], str]:
#     """Prepare JavaScript specific metrics for database storage."""
#     pass

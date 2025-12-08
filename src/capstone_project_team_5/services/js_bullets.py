"""
Local bullet point generation for JavaScript/TypeScript projects.

Generates resume-style bullets from JS/TS project analysis without LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from capstone_project_team_5.js_code_analyzer import JSProjectSummary


def generate_js_bullets(summary: JSProjectSummary, max_bullets: int = 6) -> list[str]:
    """Generate resume bullets from JS/TS project summary.

    Args:
        summary: JSProjectSummary from js_analyzer
        max_bullets: Maximum number of bullets to generate

    Returns:
        List of professionally-written resume bullets
    """

    bullets = []

    frontend_stack = summary.tech_stack.get("frontend", [])
    backend_stack = summary.tech_stack.get("backend", [])

    if frontend_stack and backend_stack:
        frontend_str = _format_list(frontend_stack[:3])
        backend_str = _format_list(backend_stack[:3])

        scale_info = _get_scale_metrics(summary)
        bullets.append(
            f"Engineered a full-stack application using {frontend_str} on the frontend "
            f"and {backend_str} on the backend{scale_info}"
        )
    elif frontend_stack:
        stack_str = _format_list(frontend_stack[:3])
        scale_info = _get_scale_metrics(summary)
        bullets.append(f"Built a responsive web application with {stack_str}{scale_info}")
    elif backend_stack:
        stack_str = _format_list(backend_stack[:3])
        scale_info = _get_scale_metrics(summary)
        bullets.append(f"Developed a scalable backend service using {stack_str}{scale_info}")
    elif summary.uses_typescript:
        scale_info = _get_scale_metrics(summary)
        bullets.append(f"Created a TypeScript application with type-safe code{scale_info}")
    else:
        scale_info = _get_scale_metrics(summary)
        bullets.append(f"Developed a JavaScript application{scale_info}")

    if summary.total_classes > 0 and summary.oop_features:
        oop_str = _format_list(list(summary.oop_features)[:3])
        bullets.append(
            f"Architected {summary.total_classes} class{'es' if summary.total_classes > 1 else ''} "
            f"utilizing {oop_str} for maintainable object-oriented design"
        )

    if summary.total_functions > 10:
        complexity_desc = _get_complexity_description(summary.avg_function_complexity)
        bullets.append(
            f"Implemented {summary.total_functions} functions with {complexity_desc} "
            f"following clean code principles and SOLID design patterns"
        )

    features = summary.features
    if features:
        if len(features) >= 4:
            feature_str = _format_list(features)
            bullets.append(
                f"Implemented {len(features)} key features including {feature_str} "
                f"to enhance user experience and functionality"
            )
        elif len(features) >= 2:
            feature_str = _format_list(features)
            bullets.append(f"Integrated {feature_str} for comprehensive user experience")
        else:
            bullets.append(f"Implemented {features[0]} with robust error handling and validation")

    if summary.uses_react:
        state_mgmt = [
            item
            for item in frontend_stack
            if "Redux" in item or "Zustand" in item or "Recoil" in item or "MobX" in item
        ]

        if state_mgmt:
            bullets.append(
                f"Architected state management using {state_mgmt[0]} "
                f"with React components for predictable data flow"
            )
        elif summary.custom_hooks_count > 0:
            bullets.append(
                f"Built {summary.custom_hooks_count} custom React hooks and reusable components "
                f"following modern functional patterns for maintainable UI architecture"
            )
        else:
            bullets.append(
                "Built reusable React components following modern hooks patterns "
                "for maintainable UI architecture"
            )
    elif summary.uses_vue:
        bullets.append(
            "Designed Vue.js components with reactive state management for dynamic user interfaces"
        )
    elif summary.uses_angular:
        bullets.append(
            "Developed Angular modules with dependency injection "
            "and TypeScript for enterprise-grade architecture"
        )
    elif summary.uses_nodejs and backend_stack:
        bullets.append(
            "Architected a Node.js backend with modular routing and middleware "
            "for scalable API architecture"
        )

    if summary.uses_async_await and summary.total_functions > 5:
        bullets.append(
            "Leveraged asynchronous programming with async/await patterns "
            "to optimize performance and handle concurrent operations efficiently"
        )

    if backend_stack:
        database_stack = summary.tech_stack.get("database", [])
        if database_stack:
            db_str = _format_list(database_stack[:2])
            bullets.append(
                f"Designed RESTful APIs with {db_str} persistence layer "
                f"implementing CRUD operations and efficient data access patterns"
            )
        elif any("GraphQL" in item for item in backend_stack):
            bullets.append(
                "Architected a GraphQL API schema enabling flexible client queries "
                "and optimized data fetching with resolver patterns"
            )
        else:
            bullets.append(
                "Built RESTful API endpoints with proper error handling, "
                "validation middleware, and secure authentication"
            )

    if summary.design_patterns and len(summary.design_patterns) >= 2:
        pattern_str = _format_list(list(summary.design_patterns)[:3])
        bullets.append(
            f"Applied {pattern_str} to create scalable, "
            f"maintainable architecture with separation of concerns"
        )

    if summary.data_structures and summary.algorithms_used:
        ds_str = _format_list(list(summary.data_structures)[:2])
        algo_str = _format_list(list(summary.algorithms_used)[:2])
        bullets.append(
            f"Utilized {ds_str} data structures and {algo_str} algorithms "
            f"for efficient data processing and optimal performance"
        )
    elif summary.algorithms_used and len(summary.algorithms_used) >= 2:
        algo_str = _format_list(list(summary.algorithms_used)[:3])
        bullets.append(f"Implemented {algo_str} for optimized data processing and computation")

    integrations = summary.integrations
    if integrations:
        priority_order = ["payment", "auth", "cloud", "realtime", "visualization"]
        for category in priority_order:
            if category in integrations and integrations[category]:
                services = integrations[category]
                category_names = {
                    "payment": "payment processing",
                    "auth": "authentication and authorization",
                    "cloud": "cloud services",
                    "realtime": "real-time communication",
                    "visualization": "data visualization",
                }
                service_str = _format_list(services[:2])
                bullets.append(
                    f"Integrated {service_str} for {category_names[category]} "
                    f"with secure API handling and error recovery"
                )
                break

    testing_stack = summary.tech_stack.get("testing", [])
    if testing_stack:
        test_str = _format_list(testing_stack[:2])
        bullets.append(
            f"Established comprehensive test coverage using {test_str} "
            f"ensuring code reliability and preventing regressions"
        )

    if summary.total_imports > 20 or summary.total_exports > 10:
        bullets.append(
            f"Designed modular architecture with {summary.total_exports} exported modules "
            f"promoting code reusability and separation of concerns"
        )

    tooling = summary.tech_stack.get("tooling", [])
    if tooling and len(tooling) >= 2:
        tool_str = _format_list(tooling[:3])
        bullets.append(
            f"Configured modern development workflow with {tool_str} "
            f"for optimized builds, code quality, and developer experience"
        )

    if summary.uses_typescript and "TypeScript" in frontend_stack:
        bullets.append(
            "Leveraged TypeScript's static typing and interfaces "
            "to catch errors at compile-time and improve code maintainability"
        )

    ui_libs = [
        item
        for item in frontend_stack
        if any(
            ui in item for ui in ["Material-UI", "Ant Design", "Tailwind", "Chakra", "Bootstrap"]
        )
    ]

    if ui_libs and "Responsive Design" in features:
        bullets.append(
            f"Designed responsive interfaces using {ui_libs[0]} "
            f"with mobile-first approach and WCAG accessibility standards"
        )

    return bullets[:max_bullets]


def _get_scale_metrics(summary: JSProjectSummary) -> str:
    """Generate scale/size metrics for the project.

    Args:
        summary: Project summary with metrics

    Returns:
        Formatted string with scale information
    """

    metrics = []

    if summary.total_files > 0:
        metrics.append(f"{summary.total_files} files")

    if summary.total_functions > 20 or summary.total_functions > 0:
        metrics.append(f"{summary.total_functions} functions")

    if summary.total_lines_of_code > 1000:
        loc_k = summary.total_lines_of_code / 1000
        metrics.append(f"{loc_k:.1f}K lines of code")

    if not metrics:
        return ""

    if len(metrics) == 1:
        return f" spanning {metrics[0]}"
    elif len(metrics) == 2:
        return f" across {metrics[0]} and {metrics[1]}"
    else:
        return f" across {metrics[0]}, {metrics[1]}, and {metrics[2]}"


def _get_complexity_description(avg_complexity: float) -> str:
    """Get a description of code complexity.

    Args:
        avg_complexity: Average cyclomatic complexity

    Returns:
        Human-readable complexity description
    """

    if avg_complexity == 0:
        return "clean, maintainable code"
    elif avg_complexity < 3:
        return "low complexity and high maintainability"
    elif avg_complexity < 5:
        return "moderate complexity and balanced design"
    elif avg_complexity < 8:
        return "well-structured complex logic"
    else:
        return "sophisticated algorithmic complexity"


def generate_js_project_bullets(project_path: Path, max_bullets: int = 6) -> list[str]:
    """Generate bullets by analyzing a JS/TS project from scratch.

    Args:
        project_path: Path to the project directory
        max_bullets: Maximum bullets to generate

    Returns:
        List of resume bullets
    """

    from capstone_project_team_5.detection import identify_language_and_framework
    from capstone_project_team_5.js_code_analyzer import analyze_js_project

    language, framework = identify_language_and_framework(project_path)
    summary = analyze_js_project(project_path, language, framework)

    return generate_js_bullets(summary, max_bullets=max_bullets)


def _format_list(items: list[str]) -> str:
    """Format a list of items naturally for bullets.

    Args:
        items: List of strings to format

    Returns:
        Formatted string (e.g., "A, B, and C")
    """

    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"

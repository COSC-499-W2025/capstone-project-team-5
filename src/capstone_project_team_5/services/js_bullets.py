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
        bullets.append(
            f"Engineered a full-stack application using {frontend_str} on the frontend "
            f"and {backend_str} on the backend across {summary.total_files} files"
        )
    elif frontend_stack:
        stack_str = _format_list(frontend_stack[:3])
        bullets.append(
            f"Built a responsive web application with {stack_str} featuring "
            f"{summary.total_files} modular components"
        )
    elif backend_stack:
        stack_str = _format_list(backend_stack[:3])
        bullets.append(
            f"Developed a scalable backend service using {stack_str} "
            f"handling API requests and business logic"
        )
    elif summary.uses_typescript:
        bullets.append(
            f"Created a TypeScript application with type-safe code across "
            f"{summary.total_files} files"
        )
    else:
        bullets.append(f"Developed a JavaScript application spanning {summary.total_files} files")

    features = summary.features
    if features:
        if len(features) >= 4:
            feature_str = _format_list(features[:3])
            bullets.append(
                f"Implemented {len(features)} key features including {feature_str} "
                f"to enhance user experience"
            )
        elif len(features) >= 2:
            feature_str = _format_list(features[:2])
            bullets.append(f"Integrated {feature_str} for a complete user experience")
        else:
            bullets.append(f"Implemented {features[0]} with robust error handling")

    if summary.uses_react:
        state_mgmt = [
            item
            for item in frontend_stack
            if "Redux" in item or "Zustand" in item or "Recoil" in item
        ]
        if state_mgmt:
            bullets.append(
                f"Architected state management using {state_mgmt[0]} "
                f"with React components for predictable data flow"
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

    if backend_stack:
        database_stack = summary.tech_stack.get("database", [])
        if database_stack:
            db_str = _format_list(database_stack[:2])
            bullets.append(
                f"Designed RESTful APIs with {db_str} persistence layer "
                f"for efficient data operations"
            )
        elif any("GraphQL" in item for item in backend_stack):
            bullets.append(
                "Architected a GraphQL API schema enabling flexible client queries "
                "and optimized data fetching"
            )
        else:
            bullets.append(
                "Built RESTful API endpoints with proper error handling and validation middleware"
            )

    integrations = summary.integrations
    if integrations:
        priority_order = ["payment", "auth", "cloud", "realtime"]
        for category in priority_order:
            if category in integrations and integrations[category]:
                services = integrations[category]
                category_names = {
                    "payment": "payment processing",
                    "auth": "authentication",
                    "cloud": "cloud services",
                    "realtime": "real-time communication",
                }
                service_str = _format_list(services[:2])
                bullets.append(
                    f"Integrated {service_str} for {category_names[category]} "
                    f"with secure API handling"
                )
                break

    testing_stack = summary.tech_stack.get("testing", [])
    if testing_stack:
        test_str = _format_list(testing_stack[:2])
        bullets.append(
            f"Established comprehensive test coverage using {test_str} "
            f"ensuring code reliability and preventing regressions"
        )

    tooling = summary.tech_stack.get("tooling", [])
    if tooling:
        tool_str = _format_list(tooling[:3])
        bullets.append(
            f"Configured modern development workflow with {tool_str} "
            f"for optimized builds and code quality"
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
            f"with mobile-first approach and accessibility standards"
        )

    return bullets[:max_bullets]


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

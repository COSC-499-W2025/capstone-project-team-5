from __future__ import annotations

import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from capstone_project_team_5.collab_detect import CollabDetector
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.file_walker import DirectoryWalker
from capstone_project_team_5.models.upload import DetectedProject
from capstone_project_team_5.role_detector import detect_user_role
from capstone_project_team_5.services.bullet_generator import (
    build_testing_bullet,
    generate_resume_bullets,
)
from capstone_project_team_5.services.code_analysis_persistence import (
    save_code_analysis_to_db,
)
from capstone_project_team_5.services.project_analysis import ProjectAnalysis, analyze_project
from capstone_project_team_5.skill_detection import extract_project_tools_practices
from capstone_project_team_5.utils.git import (
    AuthorContribution,
    get_author_contributions,
    get_current_git_identity,
    get_weekly_activity,
    is_git_repo,
    render_weekly_activity_chart,
)

_EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".cs": "C#",
    ".c": "C/C++",
    ".cc": "C/C++",
    ".cpp": "C/C++",
    ".cxx": "C/C++",
    ".h": "C/C++",
    ".hpp": "C/C++",
    ".rs": "Rust",
    ".go": "Go",
    ".php": "PHP",
    ".rb": "Ruby",
    ".kt": "Kotlin",
    ".swift": "Swift",
}


def _detect_languages_from_walk(walk_result: Any) -> set[str]:
    """Infer all languages present in a project from file extensions."""

    languages: set[str] = set()
    for file_info in getattr(walk_result, "files", []):
        try:
            suffix = Path(file_info.path).suffix.lower()
        except Exception:
            continue
        mapped = _EXTENSION_LANGUAGE_MAP.get(suffix)
        if mapped is not None:
            languages.add(mapped)
    return languages


def _resolve_project_path(base: Path, rel_path: str) -> Path | None:
    """Resolve project path within extraction directory, skipping pseudo-projects."""

    normalized = rel_path.strip()
    if not normalized:
        return None

    segments = [
        segment for segment in normalized.split("/") if segment and segment not in {"..", "."}
    ]
    if not segments:
        return None
    return base.joinpath(*segments)


def _format_bytes(size: int) -> str:
    """Format bytes into a human-readable string."""

    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def _ai_bullet_permission(consent_tool: ConsentTool) -> tuple[bool, str | None]:
    """Determine whether AI bullet generation is permitted."""

    if not consent_tool.use_external_services:
        return (
            False,
            "\n⚠️  External services consent not given; skipping AI bullet generation.",
        )

    services = getattr(consent_tool, "external_services", {})
    if isinstance(services, dict):
        service_names = services.keys()
    elif isinstance(services, (set, list, tuple)):
        service_names = services
    else:
        service_names = []

    if "Gemini" not in set(str(name) for name in service_names):
        return (
            False,
            "\n⚠️  Gemini not enabled in external services; skipping AI bullet generation.",
        )

    return True, None


def analyze_projects_structured(
    extract_root: Path,
    projects: Sequence[DetectedProject],
    consent_tool: ConsentTool,
    current_user: str | None = None,
) -> list[dict[str, Any]]:
    """Compute structured per-project analysis for all detected projects."""

    ai_allowed, ai_warning_global = _ai_bullet_permission(consent_tool)
    analyses: list[dict[str, Any]] = []
    ai_available = bool(os.getenv("GEMINI_API_KEY"))

    for project in projects:
        project_path = _resolve_project_path(extract_root, project.rel_path)
        if project_path is None or not project_path.is_dir():
            continue

        project_analysis: ProjectAnalysis | None = None
        try:
            project_analysis = analyze_project(project_path, consent_tool)
        except Exception:
            project_analysis = None

        try:
            walk_result = DirectoryWalker.walk(project_path)
        except ValueError:
            continue

        if project_analysis is None:
            # Skip project if analysis failed - don't retry
            continue
        analysis = project_analysis
        language = analysis.language
        framework = analysis.framework
        tools = set(analysis.tools)
        practices = set(analysis.practices)

        all_langs = _detect_languages_from_walk(walk_result)
        other_languages = sorted(lang for lang in all_langs if lang != language)

        summary = DirectoryWalker.get_summary(walk_result)
        total_size = _format_bytes(summary["total_size_bytes"])

        collab_summary = CollabDetector.collaborator_summary(project_path)
        collaborators_display = CollabDetector.format_collaborators(collab_summary)

        duration_timedelta, duration_display = ContributionMetrics.get_project_duration(
            project_path
        )
        contribution_metrics, metrics_source = ContributionMetrics.get_project_contribution_metrics(
            project_path
        )

        score, breakdown = ContributionMetrics.calculate_importance_score(
            contribution_metrics, duration_timedelta, project.file_count
        )

        resume_bullets: list[str] = []
        resume_source = "Local"
        ai_warning: str | None = ai_warning_global if not ai_allowed else None

        try:
            resume_bullets, resume_source = generate_resume_bullets(
                project_path,
                max_bullets=6,
                use_ai=ai_allowed,
                ai_available=ai_available,
                analysis=analysis,
            )
        except Exception as exc:
            ai_warning = f"Resume bullets error: {exc}"

        git_is_repo = is_git_repo(project_path)
        git_current_author: str | None = None
        git_author_contribs: list[dict[str, int | str]] = []
        git_current_contrib: dict[str, int] | None = None
        git_activity_chart: list[str] = []

        if git_is_repo:
            current_name, _current_email = get_current_git_identity(project_path)
            git_current_author = current_name

            try:
                contributions: list[AuthorContribution] = get_author_contributions(project_path)
            except RuntimeError:
                contributions = []

            # Detect user role based on Git contributions
            user_role_info = detect_user_role(
                project_path, current_name, contributions, collab_summary[0]
            )
            if user_role_info:
                analysis.user_role = user_role_info.role
                analysis.user_contribution_percentage = user_role_info.contribution_percentage
                analysis.role_justification = user_role_info.justification

            for ac in contributions:
                git_author_contribs.append(
                    {
                        "author": ac.author,
                        "commits": ac.commits,
                        "added": ac.added,
                        "deleted": ac.deleted,
                    }
                )
                if (
                    current_name is not None
                    and ac.author.strip().lower() == current_name.strip().lower()
                ):
                    git_current_contrib = {
                        "commits": ac.commits,
                        "added": ac.added,
                        "deleted": ac.deleted,
                    }

            try:
                activity = get_weekly_activity(project_path, weeks=12)
                git_activity_chart = render_weekly_activity_chart(activity)
            except RuntimeError:
                git_activity_chart = []

        save_code_analysis_to_db(project.name, project.rel_path, analysis, username=current_user)
        skill_timeline = _get_skill_timeline_for_project(project.name, project.rel_path)

        analyses.append(
            {
                "name": project.name,
                "rel_path": project.rel_path,
                "language": language,
                "framework": framework,
                "other_languages": other_languages,
                "practices": sorted(practices),
                "tools": sorted(tools),
                "duration": duration_display,
                "duration_timedelta": duration_timedelta,
                "collaborators_display": collaborators_display,
                "collaborators_raw": {
                    "count": collab_summary[0],
                    "identities": sorted(collab_summary[1]),
                },
                "file_summary": {
                    "total_files": summary["total_files"],
                    "total_size": total_size,
                    "total_size_bytes": summary["total_size_bytes"],
                },
                "contribution": {
                    "metrics": contribution_metrics,
                    "source": metrics_source,
                },
                "contribution_summary": ContributionMetrics.format_contribution_metrics(
                    contribution_metrics, metrics_source
                ),
                "score": score,
                "score_breakdown": breakdown,
                "ai_bullets": [],
                "ai_warning": ai_warning,
                "resume_bullets": resume_bullets,
                "resume_bullet_source": resume_source,
                "skill_timeline": skill_timeline,
                "git": {
                    "is_repo": git_is_repo,
                    "current_author": git_current_author,
                    "author_contributions": git_author_contribs,
                    "current_author_contribution": git_current_contrib,
                    "activity_chart": git_activity_chart,
                },
                "user_role": analysis.user_role,
                "user_contribution_percentage": analysis.user_contribution_percentage,
                "role_justification": analysis.role_justification,
            }
        )

    return analyses


def analyze_root_structured(extract_root: Path, consent_tool: ConsentTool) -> dict[str, Any]:
    """Compute a structured analysis summary for the extraction root."""

    project_analysis: ProjectAnalysis | None = None
    try:
        project_analysis = analyze_project(extract_root, consent_tool)
    except Exception:
        project_analysis = None

    walk_result = DirectoryWalker.walk(extract_root)
    language, framework = identify_language_and_framework(extract_root)
    skills = extract_project_tools_practices(extract_root, consent_tool)
    tools = set(skills.get("tools", set()))
    practices = set(skills.get("practices", set()))

    ai_allowed, ai_warning = _ai_bullet_permission(consent_tool)
    ai_available = bool(os.getenv("GEMINI_API_KEY"))

    collab_summary = CollabDetector.collaborator_summary(extract_root)
    collaborators_display = CollabDetector.format_collaborators(collab_summary)

    duration_timedelta, duration_display = ContributionMetrics.get_project_duration(extract_root)
    contribution_metrics, metrics_source = ContributionMetrics.get_project_contribution_metrics(
        extract_root
    )
    contribution_summary = ContributionMetrics.format_contribution_metrics(
        contribution_metrics, metrics_source
    )

    summary = DirectoryWalker.get_summary(walk_result)
    total_size = _format_bytes(summary["total_size_bytes"])

    resume_bullets: list[str] = []
    resume_source = "Local"
    ai_warning_out: str | None = ai_warning

    try:
        resume_bullets, resume_source = generate_resume_bullets(
            extract_root,
            max_bullets=6,
            use_ai=ai_allowed,
            ai_available=ai_available,
            analysis=project_analysis,
        )
    except Exception as exc:
        ai_warning_out = f"Resume bullets error: {exc}"

    if project_analysis:
        testing_bullet = build_testing_bullet(project_analysis)
        if testing_bullet and testing_bullet not in resume_bullets:
            resume_bullets = list(resume_bullets) + [testing_bullet]

    return {
        "language": language,
        "framework": framework,
        "practices": sorted(practices),
        "tools": sorted(tools),
        "duration": duration_display,
        "duration_timedelta": duration_timedelta,
        "collaborators_display": collaborators_display,
        "collaborators_raw": {
            "count": collab_summary[0],
            "identities": sorted(collab_summary[1]),
        },
        "file_summary": {
            "total_files": summary["total_files"],
            "total_size": total_size,
            "total_size_bytes": summary["total_size_bytes"],
        },
        "contribution": {
            "metrics": contribution_metrics,
            "source": metrics_source,
        },
        "contribution_summary": contribution_summary,
        "ai_bullets": [],
        "ai_warning": ai_warning_out,
        "resume_bullets": resume_bullets,
        "resume_bullet_source": resume_source,
    }


def _get_skill_timeline_for_project(name: str, rel_path: str) -> list[dict[str, Any]]:
    """Build a simple skill timeline from saved analyses."""

    try:
        from capstone_project_team_5.data.db import get_session
        from capstone_project_team_5.data.models import CodeAnalysis, Project
    except Exception:
        return []

    timeline: list[dict[str, Any]] = []

    try:
        with get_session() as session:
            project = (
                session.query(Project)
                .filter(Project.name == name, Project.rel_path == rel_path)
                .first()
            )
            if project is None:
                return []

            analyses = (
                session.query(CodeAnalysis)
                .filter(CodeAnalysis.project_id == project.id)
                .order_by(CodeAnalysis.created_at.asc())
                .all()
            )

            if not analyses:
                return []

            first_seen: dict[str, Any] = {}
            for row in analyses:
                try:
                    metrics = json.loads(row.metrics_json)
                except Exception:
                    continue
                tools = set(metrics.get("tools", []))
                practices = set(metrics.get("practices", []))
                skills = tools | practices
                for skill in skills:
                    if skill not in first_seen:
                        first_seen[skill] = row.created_at

            buckets: dict[str, set[str]] = {}
            for skill, dt in first_seen.items():
                date_str = dt.date().isoformat()
                buckets.setdefault(date_str, set()).add(skill)

            for date_str in sorted(buckets.keys()):
                timeline.append(
                    {
                        "date": date_str,
                        "skills": sorted(buckets[date_str]),
                    }
                )

    except Exception:
        return []

    return timeline

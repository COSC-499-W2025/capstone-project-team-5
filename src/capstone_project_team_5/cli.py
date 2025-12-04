from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from capstone_project_team_5.collab_detect import CollabDetector
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.file_walker import DirectoryWalker
from capstone_project_team_5.models import InvalidZipError
from capstone_project_team_5.models.upload import DetectedProject
from capstone_project_team_5.services import upload_zip
from capstone_project_team_5.services.bullet_generator import (
    build_testing_bullet,
    generate_resume_bullets,
)
from capstone_project_team_5.services.code_analysis_persistence import (
    save_code_analysis_to_db,
)
from capstone_project_team_5.services.llm import generate_bullet_points_from_analysis
from capstone_project_team_5.services.project_analysis import ProjectAnalysis, analyze_project
from capstone_project_team_5.services.ranking import update_project_ranks
from capstone_project_team_5.skill_detection import extract_project_tools_practices
from capstone_project_team_5.utils import display_upload_result, prompt_for_zip_file


def run_cli() -> int:
    """Run the CLI workflow: consent → zip upload → display tree.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print("=" * 60)
    print("Welcome to Zip2Job - Project Artifact Analyzer")
    print("=" * 60)
    print()

    consent_tool = ConsentTool()
    if not consent_tool.generate_consent_form():
        print("\n❌ Consent denied. Exiting.")
        return 1

    print("\n✅ Consent granted. Proceeding to file selection...\n")

    zip_path = prompt_for_zip_file()
    if not zip_path:
        print("❌ No file selected. Exiting.")
        return 1

    print(f"\n📦 Processing: {zip_path.name}")
    print("-" * 60)

    try:
        result = upload_zip(zip_path)
    except InvalidZipError as exc:
        print(f"\n❌ Error: {exc}")
        return 1

    display_upload_result(result)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with ZipFile(zip_path) as archive:
                archive.extractall(tmp_path)

            analyzed_count = _display_project_analyses(
                extract_root=tmp_path,
                projects=result.projects,
                consent_tool=consent_tool,
            )

            if analyzed_count == 0:
                _display_root_analysis(tmp_path, consent_tool)

    except Exception as exc:
        # Keep upload flow successful even if analysis fails.
        print(f"\nNote: Analysis step failed: {exc}")
    return 0


def _display_project_analyses(
    *, extract_root: Path, projects: Sequence[DetectedProject], consent_tool: ConsentTool
) -> int:
    """Display per-project analysis details.

    Args:
        extract_root: Temporary directory where the archive was extracted.
        projects: Projects detected during upload processing.
        consent_tool: Active consent tool with external service preferences.

    Returns:
        Number of projects successfully analyzed.
    """

    ai_allowed, ai_warning = _ai_bullet_permission(consent_tool)
    ai_warning_printed = False
    analyzed = 0
    project_scores: list[tuple[str, str, float, dict[str, float]]] = []

    for project in projects:
        project_path = _resolve_project_path(extract_root, project.rel_path)
        if project_path is None or not project_path.is_dir():
            continue

        try:
            walk_result = DirectoryWalker.walk(project_path)
        except ValueError:
            continue

        # Run unified analysis once (includes language detection, skills, C++ analyzer, etc.)
        analysis = analyze_project(project_path, consent_tool)
        language = analysis.language
        framework = analysis.framework
        tools = analysis.tools
        practices = analysis.practices
        summary = DirectoryWalker.get_summary(walk_result)
        total_size = _format_bytes(summary["total_size_bytes"])
        collab_summary = CollabDetector.collaborator_summary(project_path)
        collaborators = CollabDetector.format_collaborators(collab_summary)
        duration_timedelta, project_duration = ContributionMetrics.get_project_duration(
            project_path
        )
        contribution_metrics, metrics_source = ContributionMetrics.get_project_contribution_metrics(
            project_path
        )

        score, breakdown = ContributionMetrics.calculate_importance_score(
            contribution_metrics, duration_timedelta, project.file_count
        )
        project_scores.append((project.name, project.rel_path, score, breakdown))

        if analyzed == 0:
            print("\n📊 Project Analysis")
        print("-" * 60)
        print(f"📁 Project: {project.name}")
        print(f"Path: {project.rel_path}")
        print(f"📅 Project Duration: {project_duration}")
        print(collaborators)
        print(f"🧑‍💻 Language: {language}")
        print(f"🏗️ Framework: {framework or 'None detected'}")
        practices_list = ", ".join(sorted(practices)) or "None detected"
        tools_list = ", ".join(sorted(tools)) or "None detected"
        print(f"🧠 Practices: {practices_list}")
        print(f"🧰 Tools: {tools_list}")
        print(ContributionMetrics.format_contribution_metrics(contribution_metrics, metrics_source))

        print(f"\n{ContributionMetrics.format_score_breakdown(score, breakdown)}")

        print("\n📂 File Analysis")
        print("-" * 60)
        print(f"Total: {summary['total_files']} files ({total_size})")

        ai_warning_printed = _emit_ai_bullet_points(
            project_path=project_path,
            analysis=analysis,
            ai_allowed=ai_allowed,
            ai_warning=ai_warning,
            warning_printed=ai_warning_printed,
        )

        # Save analysis to database (language-agnostic, CLI not tied to a user)
        save_code_analysis_to_db(project.name, project.rel_path, analysis)

        analyzed += 1
        print()

    if project_scores and analyzed > 0:
        # Update DB with importance ranks/scores.
        update_project_ranks(project_scores)

        # Also show a local ranking summary for this upload.
        indexed: list[tuple[int, float]] = [(i, entry[2]) for i, entry in enumerate(project_scores)]
        ranked = ContributionMetrics.rank_projects(indexed)
        rank_by_index = {idx: rank for idx, rank in ranked}

        print("\n🏆 Project Rankings")
        print("-" * 60)
        for idx, rank in sorted(rank_by_index.items(), key=lambda pair: pair[1]):
            name, rel_path, score, _breakdown = project_scores[idx]
            rel_display = rel_path or "(root)"
            print(f"#{rank}  {name} ({rel_display}) — score {score:.1f}")

    return analyzed


def _display_root_analysis(extract_root: Path, consent_tool: ConsentTool) -> None:
    """Display analysis summary for the entire extraction root."""

    data = analyze_root_structured(extract_root, consent_tool)

    print("\n📊 Analysis Summary")
    print("-" * 60)
    print(f"📅 Project Duration: {data['duration']}")
    print(data["collaborators_display"])
    print(f"🧑‍💻 Language: {data['language']}")
    print(f"🏗️ Framework: {data['framework'] or 'None detected'}")
    practices_list = ", ".join(data["practices"]) or "None detected"
    tools_list = ", ".join(data["tools"]) or "None detected"
    print(f"🧠 Practices: {practices_list}")
    print(f"🧰 Tools: {tools_list}")
    print(data["contribution_summary"])

    print("\n📂 File Analysis")
    print("-" * 60)
    file_summary = data["file_summary"]
    print(f"Total: {file_summary['total_files']} files ({file_summary['total_size']})")

    ai_allowed, ai_warning = _ai_bullet_permission(consent_tool)
    _emit_ai_bullet_points(
        project_path=extract_root,
        analysis=None,
        ai_allowed=ai_allowed,
        ai_warning=ai_warning,
        warning_printed=False,
    )


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


def _emit_ai_bullet_points(
    *,
    project_path: Path,
    analysis: ProjectAnalysis | None = None,
    ai_allowed: bool,
    ai_warning: str | None,
    warning_printed: bool,
) -> bool:
    """Generate and print resume bullets with proper AI/local fallback.

    This now uses the unified bullet generation system that:
    1. Uses pre-computed analysis if provided (avoids redundant analysis)
    2. Tries AI generation first if permitted
    3. Falls back to local generation automatically

    Args:
        project_path: Path to project directory
        analysis: Pre-computed ProjectAnalysis (avoids redundant C++ analyzer calls)
        ai_allowed: Whether AI generation is permitted (consent)
        ai_warning: Warning message if AI not allowed
        warning_printed: Whether warning has been printed already

    Returns:
        Updated warning_printed flag
    """
    # Determine if AI is available (check for API key)
    # Determine if AI is available (check for API key)
    import os

    ai_available = bool(os.getenv("GOOGLE_API_KEY"))
    # Use unified bullet generator with proper fallback
    try:
        bullets, source = generate_resume_bullets(
            project_path,
            max_bullets=6,
            use_ai=ai_allowed,
            ai_available=ai_available,
            analysis=analysis,
        )

        if bullets:
            print(f"\nResume Bullet Points ({source} Generation)")
            print("-" * 60)
            for bullet in bullets:
                print(f"- {bullet}")
        else:
            print("\nNo bullet points could be generated.")

        return warning_printed

    except Exception as exc:
        print(f"\nBullet generation error: {exc}")

    # Print warning if AI was not allowed
    if not ai_allowed and not warning_printed and ai_warning is not None:
        print(ai_warning)
        return True

    return warning_printed


def _format_bytes(size: int) -> str:
    """Format bytes into human-readable string.

    Args:
        size: Size in bytes.

    Returns:
        Formatted string (e.g., "1.5 KB", "2.3 MB").
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


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
    """Infer all languages present in a project from file extensions.

    This is a lightweight signal to show polyglot projects alongside the
    primary detected language/framework.
    """
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


def analyze_projects_structured(
    extract_root: Path,
    projects: Sequence[DetectedProject],
    consent_tool: ConsentTool,
    current_user: str | None = None,
) -> list[dict[str, Any]]:
    """Compute structured per-project analysis for all detected projects.

    This is used by the TUI; the CLI continues to use the print-based
    `_display_project_analyses` for backwards-compatible output.
    """
    ai_allowed, ai_warning_global = _ai_bullet_permission(consent_tool)
    analyses: list[dict[str, Any]] = []

    import os

    from capstone_project_team_5.services.code_analysis_persistence import (
        save_code_analysis_to_db,
    )
    from capstone_project_team_5.services.project_analysis import analyze_project
    from capstone_project_team_5.utils.git import (
        AuthorContribution,
        get_author_contributions,
        get_current_git_identity,
        get_weekly_activity,
        is_git_repo,
        render_weekly_activity_chart,
    )

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

        # Unified analysis object (language, skills, language-specific metrics).
        analysis = project_analysis or analyze_project(project_path, consent_tool)
        language = analysis.language
        framework = analysis.framework
        tools = set(analysis.tools)
        practices = set(analysis.practices)

        # Detect additional languages beyond the primary.
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

        ai_bullets: list[str] = []
        ai_warning: str | None = None

        if ai_allowed:
            try:
                ai_bullets = generate_bullet_points_from_analysis(
                    language=language,
                    framework=framework,
                    practices=sorted(practices),
                    tools=sorted(tools),
                    max_bullets=6,
                )
                if not ai_bullets:
                    ai_warning = "AI Bullets: provider returned no content."
            except Exception as exc:  # pragma: no cover - defensive
                ai_warning = f"AI Bullets error: {exc}"
        else:
            ai_warning = ai_warning_global

        # Unified resume bullets (AI or local-only depending on consent).
        ai_available = bool(os.getenv("GOOGLE_API_KEY"))
        try:
            resume_bullets, resume_source = generate_resume_bullets(
                project_path,
                max_bullets=6,
                use_ai=ai_allowed,
                ai_available=ai_available,
                analysis=analysis,
            )
        except Exception:
            resume_bullets = []
            resume_source = "error"

        # Git-based contribution details for collaborative projects.
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

        # Persist analysis snapshot and then build skill timeline. When a
        # user is logged in via the TUI, the snapshot is linked to that user.
        save_code_analysis_to_db(project.name, project.rel_path, analysis, username=current_user)
        skill_timeline = _get_skill_timeline_for_project(project.name, project.rel_path)

        # Optionally add a testing-focused bullet derived from the full project
        # analysis, ensuring it appears alongside any other AI bullets.
        if project_analysis:
            testing_bullet = build_testing_bullet(project_analysis)
            if testing_bullet:
                ai_bullets = list(ai_bullets)
                ai_bullets.append(testing_bullet)

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
                "ai_bullets": ai_bullets,
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
            }
        )

    return analyses


def analyze_root_structured(extract_root: Path, consent_tool: ConsentTool) -> dict[str, Any]:
    """Compute a structured analysis summary for the extraction root.

    This is used by the TUI and reused by the CLI printing path.
    """
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

    ai_bullets: list[str] = []
    ai_warning_out: str | None = None

    if ai_allowed:
        try:
            ai_bullets = generate_bullet_points_from_analysis(
                language=language,
                framework=framework,
                practices=sorted(practices),
                tools=sorted(tools),
                max_bullets=6,
            )
            if not ai_bullets:
                ai_warning_out = "AI Bullets: provider returned no content."
        except Exception as exc:  # pragma: no cover - defensive
            ai_warning_out = f"AI Bullets error: {exc}"
    else:
        ai_warning_out = ai_warning

    if project_analysis:
        testing_bullet = build_testing_bullet(project_analysis)
        if testing_bullet:
            ai_bullets = list(ai_bullets)
            ai_bullets.append(testing_bullet)

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
        "ai_bullets": ai_bullets,
        "ai_warning": ai_warning_out,
    }


def _get_skill_timeline_for_project(name: str, rel_path: str) -> list[dict[str, Any]]:
    """Build a simple 'skills over time' timeline from code_analyses snapshots.

    Groups tools+practices by the date they first appear in metrics_json.
    Returns a list of dicts: {"date": "YYYY-MM-DD", "skills": [...]}, sorted by date.
    """
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


def main() -> int:
    """Entry point for the CLI application."""
    try:
        return run_cli()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting.")
        return 130
    except Exception as exc:
        print(f"\n❌ Unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

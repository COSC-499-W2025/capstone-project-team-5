from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from capstone_project_team_5.collab_detect import CollabDetector
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.file_walker import DirectoryWalker
from capstone_project_team_5.models import InvalidZipError
from capstone_project_team_5.models.upload import DetectedProject
from capstone_project_team_5.services import upload_zip
from capstone_project_team_5.services.bullet_generator import generate_resume_bullets
from capstone_project_team_5.services.code_analysis_persistence import save_code_analysis_to_db
from capstone_project_team_5.services.project_analysis import ProjectAnalysis, analyze_project
from capstone_project_team_5.services.ranking import update_project_ranks
from capstone_project_team_5.utils import display_upload_result, prompt_for_zip_file
from capstone_project_team_5.workflows import analysis_pipeline
from capstone_project_team_5.workflows.analysis_pipeline import (
    analyze_root_structured,
)


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

    ai_allowed, ai_warning = analysis_pipeline._ai_bullet_permission(consent_tool)

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
        total_size = analysis_pipeline._format_bytes(summary["total_size_bytes"])
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

    ai_allowed, ai_warning = analysis_pipeline._ai_bullet_permission(consent_tool)
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


# NOTE: AI permission and structured analysis helpers moved to workflows.analysis_pipeline


def _emit_ai_bullet_points(
    *,
    project_path: Path,
    analysis: ProjectAnalysis | None = None,
    ai_allowed: bool,
    ai_warning: str | None,
    warning_printed: bool,
) -> bool:
    """Generate and print resume bullets with proper AI/local fallback."""

    ai_available = bool(os.getenv("GEMINI_API_KEY"))

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

    if not ai_allowed and not warning_printed and ai_warning is not None:
        print(ai_warning)
        return True

    return warning_printed


def _get_skill_timeline_for_project(name: str, rel_path: str) -> list[dict[str, Any]]:
    """Build a simple 'skills over time' timeline from code_analyses snapshots.

    Groups tools+practices by the date they first appear in metrics_json.
    Returns a list of dicts: {"date": "YYYY-MM-DD", "skills": [...]}, sorted by date.
    """
    import json

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

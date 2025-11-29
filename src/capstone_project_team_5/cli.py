from __future__ import annotations

import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from zipfile import ZipFile

from capstone_project_team_5.collab_detect import CollabDetector
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.file_walker import DirectoryWalker
from capstone_project_team_5.models import InvalidZipError
from capstone_project_team_5.models.upload import DetectedProject
from capstone_project_team_5.services import upload_zip
from capstone_project_team_5.services.bullet_generator import generate_resume_bullets
from capstone_project_team_5.services.code_analysis_persistence import (
    save_code_analysis_to_db,
)
from capstone_project_team_5.services.project_analysis import ProjectAnalysis
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
        from capstone_project_team_5.services.project_analysis import analyze_project

        analysis = analyze_project(project_path)
        language = analysis.language
        framework = analysis.framework
        tools = analysis.tools
        practices = analysis.practices
        combined_skills = tools | practices
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
        skills_list = ", ".join(sorted(combined_skills)) or "None detected"
        tools_list = ", ".join(sorted(tools)) or "None detected"
        print(f"🧠 Skills: {skills_list}")
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

        # Save analysis to database (language-agnostic)
        save_code_analysis_to_db(project.name, project.rel_path, analysis)

        analyzed += 1
        print()

    if project_scores and analyzed > 0:
        update_project_ranks(project_scores)

    return analyzed


def _display_root_analysis(extract_root: Path, consent_tool: ConsentTool) -> None:
    """Display analysis summary for the entire extraction root."""

    walk_result = DirectoryWalker.walk(extract_root)
    language, framework = identify_language_and_framework(extract_root)
    skills = extract_project_tools_practices(extract_root)
    tools = set(skills.get("tools", set()))
    practices = set(skills.get("practices", set()))
    combined_skills = tools | practices
    ai_allowed, ai_warning = _ai_bullet_permission(consent_tool)
    collab_summary = CollabDetector.collaborator_summary(extract_root)
    collaborators = CollabDetector.format_collaborators(collab_summary)
    project_duration = ContributionMetrics.get_project_duration(extract_root)[1]
    contribution_metrics = ContributionMetrics.get_project_contribution_metrics(extract_root)

    print("\n📊 Analysis Summary")
    print("-" * 60)
    print(f"📅 Project Duration: {project_duration}")
    print(collaborators)
    print(f"🧑‍💻 Language: {language}")
    print(f"🏗️ Framework: {framework or 'None detected'}")
    skills_list = ", ".join(sorted(combined_skills)) or "None detected"
    tools_list = ", ".join(sorted(tools)) or "None detected"
    print(f"🧠 Skills: {skills_list}")
    print(f"🧰 Tools: {tools_list}")
    print(
        ContributionMetrics.format_contribution_metrics(
            contribution_metrics[0], contribution_metrics[1]
        )
    )

    print("\n📂 File Analysis")
    print("-" * 60)
    summary = DirectoryWalker.get_summary(walk_result)
    total_size = _format_bytes(summary["total_size_bytes"])
    print(f"Total: {summary['total_files']} files ({total_size})")

    _emit_ai_bullet_points(
        project_path=extract_root,
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

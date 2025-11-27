from __future__ import annotations

import json
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from zipfile import ZipFile

from capstone_project_team_5.c_analyzer import CFileAnalyzer
from capstone_project_team_5.collab_detect import CollabDetector
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem
from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.file_walker import DirectoryWalker
from capstone_project_team_5.models import InvalidZipError
from capstone_project_team_5.models.upload import DetectedProject
from capstone_project_team_5.services import upload_zip
from capstone_project_team_5.services.llm import (
    generate_bullet_points_from_analysis,
)
from capstone_project_team_5.services.local_bullets import (
    generate_local_bullets,
    should_use_local_analysis,
)
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
    project_scores: list[tuple[str, str, float]] = []

    for project in projects:
        project_path = _resolve_project_path(extract_root, project.rel_path)
        if project_path is None or not project_path.is_dir():
            continue

        try:
            walk_result = DirectoryWalker.walk(project_path)
        except ValueError:
            continue

        language, framework = identify_language_and_framework(project_path)
        skills = extract_project_tools_practices(project_path)
        tools = set(skills.get("tools", set()))
        practices = set(skills.get("practices", set()))
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

        # Display C/C++ specific analysis if applicable (diagnostic only)
        if language == "C/C++":
            _display_c_analysis(project_path)
            _save_analysis_to_db(project.name, project.rel_path, language, project_path)

        # Determine whether to use local or AI bullet generation
        use_local = should_use_local_analysis(
            language=language, has_llm_consent=ai_allowed, llm_available=ai_allowed
        )

        if use_local:
            # Use local analysis (C/C++ or when AI not available/consented)
            try:
                local_bullets = generate_local_bullets(project_path, max_bullets=6)
                if local_bullets:
                    print("\nLocal Resume Bullets (No LLM)")
                    print("-" * 60)
                    for bullet in local_bullets:
                        print(f"- {bullet}")

                    # Save local bullets to portfolio
                    _save_bullets_to_portfolio(
                        project.name, project.rel_path, local_bullets, "Local Analysis"
                    )
            except Exception as exc:
                print(f"\nWarning: Local bullet generation failed: {exc}")
        else:
            # Try AI bullet generation with fallback to local
            ai_warning_printed = _emit_ai_bullet_points(
                language=language,
                framework=framework,
                combined_skills=combined_skills,
                tools=tools,
                ai_allowed=ai_allowed,
                ai_warning=ai_warning,
                warning_printed=ai_warning_printed,
                project_path=project_path,
                project_name=project.name,
                project_rel_path=project.rel_path,
            )

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

    # Display C/C++ specific analysis if applicable (diagnostic only)
    if language == "C/C++":
        _display_c_analysis(extract_root)

    # Determine whether to use local or AI bullet generation
    use_local = should_use_local_analysis(
        language=language, has_llm_consent=ai_allowed, llm_available=ai_allowed
    )

    if use_local:
        # Use local analysis (C/C++ or when AI not available/consented)
        try:
            local_bullets = generate_local_bullets(extract_root, max_bullets=6)
            if local_bullets:
                print("\nLocal Resume Bullets (No LLM)")
                print("-" * 60)
                for bullet in local_bullets:
                    print(f"- {bullet}")
        except Exception as exc:
            print(f"\nWarning: Local bullet generation failed: {exc}")
    else:
        # Try AI bullet generation with fallback to local
        _emit_ai_bullet_points(
            language=language,
            framework=framework,
            combined_skills=combined_skills,
            tools=tools,
            ai_allowed=ai_allowed,
            ai_warning=ai_warning,
            warning_printed=False,
            project_path=extract_root,
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


def _fallback_to_local_bullets(
    project_path: Path, project_name: str | None = None, project_rel_path: str | None = None
) -> bool:
    """Fallback to local bullet generation when AI fails or returns nothing.

    Args:
        project_path: Path to the project
        project_name: Project name (for saving bullets)
        project_rel_path: Project relative path (for saving bullets)

    Returns:
        True (warning has been handled)
    """
    try:
        local_bullets = generate_local_bullets(project_path, max_bullets=6)
        if local_bullets:
            print("\nLocal Resume Bullets (Fallback)")
            print("-" * 60)
            for bullet in local_bullets:
                print(f"- {bullet}")

            # Save local bullets to portfolio if project info provided
            if project_name and project_rel_path:
                _save_bullets_to_portfolio(
                    project_name, project_rel_path, local_bullets, "Local Fallback"
                )
        else:
            print("Warning: No bullets could be generated.")
    except Exception as exc:
        print(f"Warning: Fallback bullet generation also failed: {exc}")

    return True


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
    language: str,
    framework: str | None,
    combined_skills: set[str],
    tools: set[str],
    ai_allowed: bool,
    ai_warning: str | None,
    warning_printed: bool,
    project_path: Path | None = None,
    project_name: str | None = None,
    project_rel_path: str | None = None,
) -> bool:
    """Print AI bullet points when permitted, with fallback to local analysis.

    Args:
        language: Detected programming language
        framework: Detected framework (if any)
        combined_skills: Set of detected skills
        tools: Set of detected tools
        ai_allowed: Whether AI bullet generation is permitted
        ai_warning: Warning message if AI not allowed
        warning_printed: Whether warning has been printed
        project_path: Path to project (for fallback to local)
        project_name: Project name (for saving fallback bullets)
        project_rel_path: Project relative path (for saving fallback bullets)

    Returns:
        Updated warning_printed flag
    """

    if ai_allowed:
        try:
            ai_bullets = generate_bullet_points_from_analysis(
                language=language,
                framework=framework,
                skills=sorted(combined_skills),
                tools=sorted(tools),
                max_bullets=6,
            )

            if ai_bullets:
                print("\nAI Bullet Points")
                print("-" * 60)
                for bullet in ai_bullets:
                    print(f"- {bullet}")
                # Save AI bullets to portfolio if project info provided
                if project_name and project_rel_path and ai_bullets:
                    _save_bullets_to_portfolio(
                        project_name, project_rel_path, ai_bullets, "AI-Generated"
                    )
                return warning_printed
            else:
                print("\nAI Bullets: provider returned no content.")
                # Fallback to local if AI returns nothing
                if project_path:
                    print("Falling back to local analysis...")
                    return _fallback_to_local_bullets(project_path, project_name, project_rel_path)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"\nAI Bullets error: {exc}")
            print("\nWarning: Could not generate AI bullet points.")
            # Fallback to local analysis on error
            if project_path:
                print("Falling back to local analysis...")
                return _fallback_to_local_bullets(project_path, project_name, project_rel_path)
        return warning_printed

    if not warning_printed and ai_warning is not None:
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


def _display_c_analysis(project_path: Path) -> None:
    """Display detailed C/C++ code analysis metrics.

    Args:
        project_path: Path to the C/C++ project directory.
    """
    try:
        summary = CFileAnalyzer.analyze_project(project_path)

        if summary.total_files == 0:
            return

        print("\n🔍 C/C++ Code Analysis")
        print("-" * 60)
        print(
            f"Files: {summary.total_files} "
            f"({summary.source_files} source, {summary.header_files} headers)"
        )
        print(f"Lines of Code: {summary.total_lines_of_code:,}")
        print(f"Functions: {summary.total_functions}")

        if summary.total_structs > 0:
            print(f"Structs: {summary.total_structs}")
        if summary.total_classes > 0:
            print(f"Classes: {summary.total_classes}")

        features = []
        if summary.uses_pointers:
            features.append("Pointers")
        if summary.uses_memory_management:
            features.append("Memory Management")
        if summary.uses_concurrency:
            features.append("Concurrency")
        if summary.uses_error_handling:
            features.append("Error Handling")

        if features:
            print(f"Features: {', '.join(features)}")

        if summary.libraries_used:
            libs = sorted(summary.libraries_used)[:5]
            lib_str = ", ".join(libs)
            if len(summary.libraries_used) > 5:
                lib_str += f" (+{len(summary.libraries_used) - 5} more)"
            print(f"Libraries: {lib_str}")

        if summary.avg_complexity > 0:
            print(f"Avg Complexity: {summary.avg_complexity:.1f}")

    except Exception as exc:
        print(f"\n⚠️  C/C++ analysis failed: {exc}")


def _save_analysis_to_db(
    project_name: str, project_rel_path: str, language: str, project_path: Path
) -> None:
    """Save code analysis results to the database.

    Args:
        project_name: Name of the project.
        project_rel_path: Relative path of the project.
        language: Programming language detected.
        project_path: Path to the project directory.
    """
    if language != "C/C++":
        return  # Currently only C/C++ is fully supported

    try:
        summary = CFileAnalyzer.analyze_project(project_path)

        if summary.total_files == 0:
            return

        # Convert summary to JSON
        metrics = {
            "total_files": summary.total_files,
            "header_files": summary.header_files,
            "source_files": summary.source_files,
            "total_lines_of_code": summary.total_lines_of_code,
            "total_functions": summary.total_functions,
            "total_structs": summary.total_structs,
            "total_classes": summary.total_classes,
            "has_main": summary.has_main,
            "libraries_used": list(summary.libraries_used),
            "avg_complexity": summary.avg_complexity,
            "uses_pointers": summary.uses_pointers,
            "uses_memory_management": summary.uses_memory_management,
            "uses_concurrency": summary.uses_concurrency,
            "uses_error_handling": summary.uses_error_handling,
        }

        summary_text = (
            f"C/C++ project with {summary.total_lines_of_code:,} LOC, "
            f"{summary.total_functions} functions"
        )

        # Save to database
        with get_session() as session:
            # Find the project by name and rel_path
            from capstone_project_team_5.data.models.project import Project

            project = (
                session.query(Project)
                .filter(Project.name == project_name, Project.rel_path == project_rel_path)
                .first()
            )

            if project:
                analysis = CodeAnalysis(
                    project_id=project.id,
                    language=language,
                    analysis_type="local",
                    metrics_json=json.dumps(metrics),
                    summary_text=summary_text,
                )
                session.add(analysis)
                session.commit()

    except Exception as exc:
        print(f"\n⚠️  Failed to save analysis to database: {exc}")


def _save_bullets_to_portfolio(
    project_name: str, project_rel_path: str, bullets: list[str], bullet_type: str = "Local"
) -> None:
    """Save generated bullet points as portfolio items.

    Args:
        project_name: Name of the project.
        project_rel_path: Relative path of the project.
        bullets: List of bullet points.
        bullet_type: Type of bullets (e.g., "Local", "AI").
    """
    if not bullets:
        return

    try:
        with get_session() as session:
            from capstone_project_team_5.data.models.project import Project

            project = (
                session.query(Project)
                .filter(Project.name == project_name, Project.rel_path == project_rel_path)
                .first()
            )

            if project:
                # Create portfolio item with bullets
                content = "\n".join(f"• {bullet}" for bullet in bullets)
                portfolio_item = PortfolioItem(
                    project_id=project.id,
                    title=f"{bullet_type} Resume Bullets - {project_name}",
                    content=content,
                )
                session.add(portfolio_item)
                session.commit()

    except Exception as exc:
        print(f"\n⚠️  Failed to save bullets to portfolio: {exc}")


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

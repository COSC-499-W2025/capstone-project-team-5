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
from capstone_project_team_5.services.llm import (
    generate_bullet_points_from_analysis,
)
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
        project_duration = ContributionMetrics.get_project_duration(project_path)[1]
        contribution_metrics = ContributionMetrics.get_project_contribution_metrics(project_path)

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
        print(
            ContributionMetrics.format_contribution_metrics(
                contribution_metrics[0], contribution_metrics[1]
            )
        )

        print("\n📂 File Analysis")
        print("-" * 60)
        print(f"Total: {summary['total_files']} files ({total_size})")

        ai_warning_printed = _emit_ai_bullet_points(
            language=language,
            framework=framework,
            combined_skills=combined_skills,
            tools=tools,
            ai_allowed=ai_allowed,
            ai_warning=ai_warning,
            warning_printed=ai_warning_printed,
        )

        analyzed += 1
        print()

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
        language=language,
        framework=framework,
        combined_skills=combined_skills,
        tools=tools,
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
    language: str,
    framework: str | None,
    combined_skills: set[str],
    tools: set[str],
    ai_allowed: bool,
    ai_warning: str | None,
    warning_printed: bool,
) -> bool:
    """Print AI bullet points when permitted, returning updated warning flag."""

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
            else:
                print("\nAI Bullets: provider returned no content.")
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"\nAI Bullets error: {exc}")
            print("\n⚠️  Could not generate AI bullet points.")
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

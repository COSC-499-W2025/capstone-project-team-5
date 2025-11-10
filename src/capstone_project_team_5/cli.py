from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile

from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.detection import identify_language_and_framework
from capstone_project_team_5.file_walker import DirectoryWalker
from capstone_project_team_5.models import InvalidZipError
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

            # Walk the extracted directory
            walk_result = DirectoryWalker.walk(tmp_path)

            language, framework = identify_language_and_framework(tmp_path)
            skills = extract_project_tools_practices(tmp_path)

            print("\n📊 Analysis Summary")
            print("-" * 60)
            print(f"🧑‍💻 Language: {language}")
            print(f"🏗️ Framework: {framework or 'None detected'}")
            combined_skills = set(skills.get("tools", set())) | set(skills.get("practices", set()))
            skills_list = ", ".join(sorted(combined_skills)) or "None detected"
            tools = ", ".join(sorted(skills.get("tools", set()))) or "None detected"
            print(f"🧠 Skills: {skills_list}")
            print(f"🧰 Tools: {tools}")

            # Display file walk statistics
            print("\n📂 File Analysis")
            print("-" * 60)
            summary = DirectoryWalker.get_summary(walk_result)
            total_size = _format_bytes(summary["total_size_bytes"])
            print(f"Total: {summary['total_files']} files ({total_size})")
            # AI-generated bullet points (always attempt; report reason on failure)
            if not consent_tool.use_external_services:
                print("\n⚠️  External services consent not given; skipping AI bullet generation.")
            elif "Gemini" not in consent_tool.external_services:
                print(
                    "\n⚠️  Gemini not enabled in external services; skipping AI bullet generation."
                )
            else:
                try:
                    ai_bullets = generate_bullet_points_from_analysis(
                        language=language,
                        framework=framework,
                        skills=sorted(combined_skills),
                        tools=sorted(skills.get("tools", set())),
                        max_bullets=6,
                    )

                    if ai_bullets:
                        print("\nAI Bullet Points")
                        print("-" * 60)
                        for b in ai_bullets:
                            print(f"- {b}")
                    else:
                        print("\nAI Bullets: provider returned no content.")
                except Exception as exc:
                    print(f"\nAI Bullets error: {exc}")
                    print("\n⚠️  Could not generate AI bullet points.")
                    print("Error: ", sys.exc_info()[1])
                    pass

    except Exception as exc:
        # Keep upload flow successful even if analysis fails.
        print(f"\nNote: Analysis step failed: {exc}")
    return 0


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

"""Quick test script for contributor analysis."""

from pathlib import Path

from capstone_project_team_5.contributor_analysis import analyze_contributors

# Analyze the current project
current_dir = Path.cwd()
result = analyze_contributors(current_dir)

contributors = result["contributors"]

print("\n" + "=" * 70)
print("📊 CONTRIBUTOR ANALYSIS TEST")
print("=" * 70)
print(f"\nRepository: {current_dir.name}")
print(f"Total Contributors: {len(contributors)}\n")

if contributors:
    print("👥 Contributors (sorted by commits):")
    print("-" * 70)
    for i, contrib in enumerate(contributors, 1):
        print(
            f"{i:2}. {contrib.name:<25} "
            f"📧 {contrib.email:<35} "
            f"💾 {contrib.commits:>3} commits, "
            f"📁 {contrib.files_modified:>3} files"
        )
else:
    print("⚠️  No contributors found (not a git repository?)")

print("=" * 70)

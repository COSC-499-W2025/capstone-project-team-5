from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from capstone_project_team_5.contribution_metrics import ContributionMetrics


def render_project_markdown(upload: dict[str, Any], proj: dict[str, Any], rank: int | None) -> str:
    parts: list[str] = []

    title = str(upload.get("filename", "Project Analysis"))
    parts.append(f"# {title}\n")

    name = str(proj.get("name", ""))
    rel_path = str(proj.get("rel_path", ""))
    heading = f"{name} (Rank #{rank})" if rank is not None else name
    parts.append(f"## {heading}\n`{rel_path}`\n")

    parts.append("### Summary")
    parts.append(f"- Duration: {proj.get('duration')}")
    parts.append(f"- Language: {proj.get('language')}")

    other = proj.get("other_languages") or []
    if other:
        parts.append(f"- Other languages: {', '.join(other)}")

    parts.append(f"- Framework: {proj.get('framework')}")

    file_summary = proj.get("file_summary") or {}
    total_files = file_summary.get("total_files", "?")
    total_size = file_summary.get("total_size", "?")
    parts.append(f"- Files: {total_files} ({total_size})")

    score = proj.get("score")
    if isinstance(score, (int, float)):
        parts.append(f"- Importance score: {score:.1f}")
        breakdown = proj.get("score_breakdown")
        if isinstance(breakdown, dict) and breakdown:
            parts.append("\n### Importance Score Breakdown")
            parts.append("```")
            parts.append(ContributionMetrics.format_score_breakdown(score, breakdown))
            parts.append("```")

    parts.append("\n### Skills - Practices")
    practices = list(_as_str_iterable(proj.get("practices") or []))
    if practices:
        parts.extend(f"- {s}" for s in practices)
    else:
        parts.append("- None detected")

    parts.append("\n### Skills - Tools")
    tools = list(_as_str_iterable(proj.get("tools") or []))
    if tools:
        parts.extend(f"- {t}" for t in tools)
    else:
        parts.append("- None detected")

    timeline = proj.get("skill_timeline") or []
    if timeline:
        parts.append("\n### Skill Development Over Time")
        for entry in timeline:
            date = entry.get("date", "")
            skills = entry.get("skills") or []
            if not skills:
                continue
            parts.append(f"- {date}: {', '.join(skills)}")

    bullets = proj.get("resume_bullets") or []
    source = proj.get("resume_bullet_source") or "unknown"
    if bullets:
        parts.append(f"\n### Resume Bullet Points ({source} Generation)")
        parts.extend(f"- {b}" for b in bullets)

    git_info = proj.get("git") or {}
    if git_info.get("is_repo"):
        current = git_info.get("current_author_contribution") or {}
        authors = git_info.get("author_contributions") or []
        if authors:
            parts.append("\n### Git Contributions")
            if current:
                parts.append(
                    f"- You: {current.get('commits', 0)} commits, "
                    f"+{current.get('added', 0)} / -{current.get('deleted', 0)} lines"
                )

            current_author = git_info.get("current_author")
            for ac in authors:
                author = ac.get("author")
                if (
                    current_author
                    and author
                    and str(author).strip().lower() == str(current_author).strip().lower()
                ):
                    continue
                parts.append(
                    f"- {author}: {ac.get('commits', 0)} commits, "
                    f"+{ac.get('added', 0)} / -{ac.get('deleted', 0)} lines"
                )

        chart_lines = git_info.get("activity_chart") or []
        if chart_lines:
            parts.append("\n### Weekly Activity (last 12 weeks)")
            parts.append("```")
            parts.extend(str(line) for line in chart_lines)
            parts.append("```")

    return "\n".join(parts)


def render_table(projects: list[dict[str, Any]]) -> str:
    """Render a simple ASCII table summary for retrieved projects."""
    headers = [
        "Name",
        "Path",
        "Language",
        "Framework",
        "Duration",
        "Files",
        "Practices",
        "Tools",
    ]
    rows: list[list[str]] = []
    for p in projects:
        name = str(p.get("name", ""))
        rel = str(p.get("rel_path", ""))
        lang = str(p.get("language", ""))
        fw = str(p.get("framework", ""))
        duration = str(p.get("duration", ""))
        files = str(p.get("file_summary", {}).get("total_files", ""))
        practices = ",".join(_as_str_iterable(p.get("practices", [])))
        tools = ",".join(_as_str_iterable(p.get("tools", [])))
        rows.append([name, rel, lang, fw, duration, files, practices, tools])

    col_widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            col_widths[i] = max(col_widths[i], len(cell))

    def fmt_row(row: list[str]) -> str:
        return " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))

    sep = "-+-".join("-" * w for w in col_widths)
    lines = [fmt_row(headers), sep]
    for r in rows:
        lines.append(fmt_row(r))

    return "```\n" + "\n".join(lines) + "\n```"


def render_detected_list(detected: list[dict[str, Any]]) -> str:
    """Render a simple markdown list of detected projects (name + rel_path)."""
    parts: list[str] = ["# Detected Projects", ""]
    if not detected:
        parts.append("(No projects detected)")
        return "\n".join(parts)

    for p in detected:
        name = p.get("name", "<unnamed>")
        rel = p.get("rel_path", "")
        files = p.get("file_count", "?")
        parts.append(f"- **{name}** — `{rel}` ({files} files)")

    return "\n".join(parts)


def render_saved_list(saved: list[dict[str, Any]]) -> str:
    """Render persisted uploads, their projects, and any saved analyses."""
    parts: list[str] = ["# Saved Uploads", ""]
    if not saved:
        parts.append("(No saved uploads found)")
        return "\n".join(parts)

    for up in saved:
        parts.append(f"## Upload: {up.get('filename')}  ")
        parts.append(f"- **ID**: {up.get('id')}  ")
        parts.append(f"- **Files**: {up.get('file_count')}  ")
        parts.append(f"- **Size**: {up.get('size_bytes'):,} bytes  ")
        parts.append(f"- **Created**: {up.get('created_at')}  ")
        projects = up.get("projects", [])
        if not projects:
            parts.append("- (No projects recorded for this upload)")
            parts.append("")
            continue

        parts.append("")
        parts.append("### Projects")
        for p in projects:
            parts.append(
                f"- **{p.get('name')}** — `{p.get('rel_path')}` ({p.get('file_count')} files)"
            )
            if p.get("importance_rank") is not None:
                parts.append(
                    f"  - Rank: {p.get('importance_rank')} — Score: {p.get('importance_score')}"
                )

            langs = p.get("languages") or []
            if langs:
                parts.append(f"  - Languages: {', '.join(langs)}")
            practices = p.get("practices") or []
            tools = p.get("tools") or []
            skills = practices + tools
            if skills:
                parts.append(f"  - Skills/Tools: {', '.join(skills[:12])}")
            loc = p.get("lines_of_code")
            if loc is not None:
                parts.append(f"  - Lines of code (sum of analyses): {loc}")

            analyses = p.get("analyses", [])
            if analyses:
                parts.append(f"  - Analyses ({p.get('analyses_count', len(analyses))}):")
                for a in analyses:
                    txt = a.get("summary_text") or "(no summary)"
                    parts.append(f"    - {a.get('language')} @ {a.get('created_at')}: {txt[:120]}")

        parts.append("")

    return "\n".join(parts)


def _as_str_iterable(values: Iterable[object]) -> Iterable[str]:
    for value in values:
        yield str(value)

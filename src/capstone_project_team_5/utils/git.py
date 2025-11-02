from __future__ import annotations

import datetime
import re
import subprocess
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from math import ceil
from pathlib import Path

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class NumstatEntry:
    """Represents one line of `git diff --numstat` output."""

    path: str
    added: int
    deleted: int


@dataclass(slots=True)
class AuthorContribution:
    """Aggregated commit statistics for an author."""

    author: str
    commits: int
    added: int
    deleted: int


# ---------------------------------------------------------------------------
# Git Execution
# ---------------------------------------------------------------------------


def run_git(repo: Path | str, *args: str) -> str:
    """Run a git command inside `repo` and return its stdout.

    Raises:
        RuntimeError: if the command exits with a non-zero status.
    """
    repo_path = Path(repo)
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"git command failed ({' '.join(args)}): {exc.stderr.strip()}") from exc


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_numstat(output: str) -> list[NumstatEntry]:
    """Convert `git diff --numstat` output to structured entries."""
    entries: list[NumstatEntry] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_s, deleted_s, path = parts[0], parts[1], parts[2]
        if added_s == "-" or deleted_s == "-":  # skip binary files
            continue
        with suppress(ValueError):
            entries.append(NumstatEntry(path, int(added_s), int(deleted_s)))
    return entries


# ---------------------------------------------------------------------------
# Contribution Summaries
# ---------------------------------------------------------------------------


def get_author_contributions(repo: Path | str, rev_range: str = "HEAD") -> list[AuthorContribution]:
    """Summarize total commits, insertions, and deletions per author."""
    raw_log = run_git(repo, "log", "--pretty=format:%H%x09%an", rev_range)
    commits = [line.split("\t", 1) for line in raw_log.splitlines() if "\t" in line]

    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # commits, added, deleted

    for commit_hash, author in commits:
        numstat = run_git(repo, "show", "--numstat", "--format=", commit_hash)
        entries = parse_numstat(numstat)
        added = sum(e.added for e in entries)
        deleted = sum(e.deleted for e in entries)
        totals[author][0] += 1
        totals[author][1] += added
        totals[author][2] += deleted

    contributions = [AuthorContribution(a, c, add, del_) for a, (c, add, del_) in totals.items()]
    contributions.sort(key=lambda ac: ac.added + ac.deleted, reverse=True)
    return contributions


def get_commit_type_counts(repo: Path | str, rev_range: str = "HEAD") -> dict[str, dict[str, int]]:
    """Classify commits by Conventional Commit type (feat, fix, docs, etc.)."""
    log_output = run_git(repo, "log", "--pretty=format:%an%x09%s", rev_range)
    pattern = re.compile(r"^(?P<type>\w+)(\([\w-]+\))?:")
    stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for line in log_output.splitlines():
        if "\t" not in line:
            continue
        author, subject = line.split("\t", 1)
        match = pattern.match(subject.strip().lower())
        commit_type = match.group("type") if match else "other"
        stats[author][commit_type] += 1

    return stats


def summarize_conventional_contributions(repo: Path | str, rev_range: str = "HEAD") -> list[str]:
    """Produce a per-author summary combining numeric and commit-type data."""
    contributions = {a.author: a for a in get_author_contributions(repo, rev_range)}
    type_counts = get_commit_type_counts(repo, rev_range)

    lines: list[str] = []
    for author, contrib in contributions.items():
        counts = type_counts.get(author, {})
        type_str = " ".join(f"{t}:{n}" for t, n in sorted(counts.items()))
        lines.append(
            f"{author:20} commits={contrib.commits:3d} "
            f"+{contrib.added:4d}/-{contrib.deleted:4d}  {type_str}"
        )
    return lines


# ---------------------------------------------------------------------------
# Weekly Activity
# ---------------------------------------------------------------------------


def get_weekly_activity(repo: Path | str, weeks: int = 12) -> dict[str, list[int]]:
    """Return per-author commit counts for the last `weeks` weeks."""
    log_output = run_git(repo, "log", "--pretty=format:%an|%ct")
    commits_by_author: dict[str, list[datetime.datetime]] = defaultdict(list)

    for line in log_output.splitlines():
        if "|" not in line:
            continue
        author, ts = line.split("|", 1)
        try:
            dt = datetime.datetime.fromtimestamp(int(ts))
        except ValueError:
            continue
        commits_by_author[author].append(dt)

    now = datetime.datetime.now()
    start = now - datetime.timedelta(weeks=weeks)

    weekly: dict[str, list[int]] = {}
    for author, times in commits_by_author.items():
        counts = [0] * weeks
        for t in times:
            if t < start:
                continue
            idx = int((t - start).days / 7)
            if 0 <= idx < weeks:
                counts[idx] += 1
        weekly[author] = counts
    return weekly


def render_weekly_activity_chart(activity: dict[str, list[int]]) -> list[str]:
    """Render an ASCII chart for per-author weekly commit counts."""
    if not activity:
        return []

    lines: list[str] = []
    max_commits = max((max(v) for v in activity.values() if v), default=1)
    blocks = "▁▂▃▄▅▆▇█"

    for author, weeks in sorted(activity.items()):
        bar = ""
        for count in weeks:
            if count <= 0:
                bar += "▁"
            else:
                level = min(ceil((count / max_commits) * (len(blocks) - 1)), len(blocks) - 1)
                bar += blocks[level]
        lines.append(f"{author:15}: {bar}")
    return lines


# ---------------------------------------------------------------------------
# Week Range Utilities
# ---------------------------------------------------------------------------


def _week_monday(d: datetime.date) -> datetime.date:
    """Return the Monday of the ISO week containing `d`."""
    return d - datetime.timedelta(days=d.weekday())


def get_weekly_activity_window(
    repo: Path | str,
    *,
    week: datetime.date | None = None,
    start_week: datetime.date | None = None,
    end_week: datetime.date | None = None,
) -> tuple[list[datetime.date], dict[str, list[int]]]:
    """Return (week_bins, per_author_counts) for a single week or a date range."""
    if week is not None:
        start_week = end_week = _week_monday(week)
    if start_week is None or end_week is None:
        return [], {}

    start = _week_monday(start_week)
    end = _week_monday(end_week)
    if end < start:
        start, end = end, start

    bins: list[datetime.date] = []
    cur = start
    while cur <= end:
        bins.append(cur)
        cur += datetime.timedelta(days=7)

    log_output = run_git(repo, "log", "--pretty=format:%an|%ct")
    counts: dict[str, list[int]] = {}

    for line in log_output.splitlines():
        if "|" not in line:
            continue
        author, ts = line.split("|", 1)
        try:
            t = datetime.datetime.fromtimestamp(int(ts))
        except ValueError:
            continue
        monday = _week_monday(t.date())
        if not (start <= monday <= end):
            continue
        idx = (monday - start).days // 7
        counts.setdefault(author, [0] * len(bins))
        counts[author][idx] += 1

    for arr in counts.values():
        if len(arr) < len(bins):
            arr.extend([0] * (len(bins) - len(arr)))

    return bins, counts


def render_weekly_activity_chart_for_range(
    repo: Path | str,
    *,
    week: datetime.date | None = None,
    start_week: datetime.date | None = None,
    end_week: datetime.date | None = None,
) -> list[str]:
    """Wrapper around `get_weekly_activity_window` that renders its output."""
    _, activity = get_weekly_activity_window(
        repo, week=week, start_week=start_week, end_week=end_week
    )
    return render_weekly_activity_chart(activity)


__all__ = [
    "NumstatEntry",
    "AuthorContribution",
    "run_git",
    "parse_numstat",
    "get_author_contributions",
    "get_commit_type_counts",
    "summarize_conventional_contributions",
    "get_weekly_activity",
    "render_weekly_activity_chart",
    "get_weekly_activity_window",
    "render_weekly_activity_chart_for_range",
]

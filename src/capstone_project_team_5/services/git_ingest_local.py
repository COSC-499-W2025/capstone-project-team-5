from __future__ import annotations

"""Local-only Git ingestion helpers (no hosting platform required).

These utilities read Git metadata from the repository on disk and map it to
the contribution metrics dataclasses so you can compute scores without any
GitHub/GitLab dependencies or tokens.
"""
# ruff: noqa: E402

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from capstone_project_team_5.services.contribution_metrics import (
    FileChange,
    PullRequest,
    Review,
)


@dataclass(slots=True)
class MergeCommit:
    sha: str
    author: str
    authored_at: datetime


def _run_git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout
    except subprocess.CalledProcessError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(f"git command failed: {' '.join(args)}: {exc.stderr}") from exc


def parse_numstat(output: str) -> list[FileChange]:
    """Parse `git diff --numstat` output into FileChange entries.

    Skips binary files which are reported with `-\t-\t<path>` by Git.
    """
    changes: list[FileChange] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added_s, deleted_s, path = parts[0], parts[1], parts[2]
        if added_s == "-" or deleted_s == "-":
            continue
        try:
            added = int(added_s)
            deleted = int(deleted_s)
        except ValueError:
            continue
        changes.append(FileChange(path=path, added=added, deleted=deleted, complexity_delta=0.0))
    return changes


def parse_review_trailers(message: str) -> list[str]:
    """Extract reviewer identities from commit message trailers.

    Recognizes lines like `Reviewed-by: Name <email>` and returns the raw
    reviewer field (e.g., `Name <email>`). Case-insensitive.
    """
    reviewers: list[str] = []
    for line in message.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("reviewed-by:"):
            value = stripped.split(":", 1)[1].strip()
            if value:
                reviewers.append(value)
    return reviewers


def _iter_merge_commits(repo: Path, since: datetime | None) -> Iterable[MergeCommit]:
    args = ["log", "--merges", "--format=%H|%an|%at"]
    if since is not None:
        # Use ISO8601 to avoid locale-specific parsing issues
        args.append(f"--since={since.astimezone(UTC).isoformat()}")
    out = _run_git(repo, *args)
    for line in out.splitlines():
        sha, author, ts = (line.split("|", 2) + [""])[:3]
        try:
            created = datetime.fromtimestamp(int(ts), tz=UTC)
        except ValueError:
            created = datetime.now(UTC)
        yield MergeCommit(sha=sha, author=author, authored_at=created)


def collect_local_prs(repo_path: Path | str, *, since: datetime | None = None) -> list[PullRequest]:
    """Collect pseudo-PRs from local merge commits.

    Each merge commit is treated as a PR. File changes are computed by diffing
    the merge commit against its first parent.
    """
    repo = Path(repo_path)
    prs: list[PullRequest] = []
    pr_id = 1
    for mc in _iter_merge_commits(repo, since):
        # first-parent diff for merged changes
        numstat = _run_git(repo, "diff", "--numstat", f"{mc.sha}^1", mc.sha)
        files = parse_numstat(numstat)
        prs.append(
            PullRequest(
                pr_id=pr_id,
                author=mc.author,
                merged=True,
                files=files,
                coverage_delta=0.0,
                performance_delta=0.0,
                created_at=mc.authored_at,
            )
        )
        pr_id += 1
    return prs


def collect_local_reviews(repo_path: Path | str, prs: list[PullRequest]) -> list[Review]:
    """Collect review hints from merge commit trailers (Reviewed-by).

    Generates one Review per reviewer occurrence with review_comments=1 and
    suggestions_accepted=0 since we cannot validate acceptance locally.
    """
    repo = Path(repo_path)
    reviews: list[Review] = []
    for pr in prs:
        # We mapped pr_id incrementally; recover the merge commit SHA via log
        # at approximate time. Since we lack an exact mapping, approximate by
        # taking the latest merge before pr.created_at.
        log = _run_git(
            repo,
            "log",
            "--merges",
            "--format=%H|%at",
            f"--until={pr.created_at.astimezone(UTC).isoformat()}",
            "-n",
            "1",
        )
        sha = (log.splitlines()[0].split("|", 1)[0]) if log.strip() else None
        if not sha:
            continue
        message = _run_git(repo, "show", "-s", "--format=%B", sha)
        for rv in parse_review_trailers(message):
            reviews.append(
                Review(pr_id=pr.pr_id, reviewer=rv, review_comments=1, suggestions_accepted=0)
            )
    return reviews


__all__ = [
    "MergeCommit",
    "parse_numstat",
    "parse_review_trailers",
    "collect_local_prs",
    "collect_local_reviews",
]

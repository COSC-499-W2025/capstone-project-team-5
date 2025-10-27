from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(slots=True)
class FileChange:
    path: str
    added: int
    deleted: int
    complexity_delta: float = 0.0


@dataclass(slots=True)
class PullRequest:
    pr_id: int
    author: str
    merged: bool
    files: Sequence[FileChange]
    coverage_delta: float = 0.0  # percentage points, e.g., +0.02 for +2pp
    performance_delta: float = 0.0  # positive is improvement (e.g., +0.10 for +10%)
    created_at: datetime = datetime.now(UTC)


@dataclass(slots=True)
class Review:
    pr_id: int
    reviewer: str
    review_comments: int
    suggestions_accepted: int


@dataclass(slots=True)
class IncidentFix:
    pr_id: int
    resolver: str
    severity: int  # 1 (low) .. 5 (critical)


def _effective_loc(added: int, deleted: int) -> float:
    # Treat deletions as half weight to avoid punishing cleanup
    return max(0, added) + 0.5 * max(0, deleted)


def _complexity_factor(delta: float) -> float:
    # Reward reductions in complexity, slightly penalize increases
    if delta <= -5:
        return 1.2
    if delta <= -1:
        return 1.1
    if delta >= 3:
        return 0.95
    return 1.0


def _per_file_criticality(
    files: Sequence[FileChange], criticality_by_path: Mapping[str, float] | None
) -> float:
    if not files:
        return 1.0
    if not criticality_by_path:
        return 1.0
    total = 0.0
    weight = 0.0
    for f in files:
        eloc = _effective_loc(f.added, f.deleted)
        total += eloc * criticality_by_path.get(f.path, 1.0)
        weight += eloc
    return (total / weight) if weight > 0 else 1.0


def _calc_pr_churn_ratio(
    pr: PullRequest, prior_prs: Iterable[PullRequest], window_days: int
) -> float:
    cutoff = pr.created_at - timedelta(days=window_days)
    touched = {fc.path for fc in pr.files}
    if not touched:
        return 0.0
    retouches = 0
    for p in prior_prs:
        if p.author != pr.author:
            continue
        if p.created_at < cutoff or p.created_at >= pr.created_at:
            continue
        prev_paths = {fc.path for fc in p.files}
        if touched & prev_paths:
            retouches += 1
    # Cap churn penalty at 0.3
    ratio = min(0.3, (retouches / max(1, len(touched))) * 0.3)
    return ratio


def compute_oaci(
    prs: Sequence[PullRequest],
    reviews: Sequence[Review],
    incidents: Sequence[IncidentFix],
    *,
    criticality_by_path: Mapping[str, float] | None = None,
    churn_window_days: int = 14,
) -> dict[str, float]:
    """Compute Ownership‑Adjusted Contribution Impact per author.

    OACI combines code changes, complexity, file criticality, churn, coverage, perf,
    review effort, and incident fixes into a single score.
    """
    # Index PRs by author and by id
    by_author: dict[str, list[PullRequest]] = defaultdict(list)
    by_id: dict[int, PullRequest] = {}
    for pr in prs:
        if not pr.merged:
            continue
        by_author[pr.author].append(pr)
        by_id[pr.pr_id] = pr

    # Pre-sort PRs by created_at for churn computation
    for lst in by_author.values():
        lst.sort(key=lambda p: p.created_at)

    result: dict[str, float] = defaultdict(float)

    # Code contributions
    for author, author_prs in by_author.items():
        for idx, pr in enumerate(author_prs):
            eloc = sum(_effective_loc(f.added, f.deleted) for f in pr.files)
            c_factor = _complexity_factor(sum(f.complexity_delta for f in pr.files))
            k_weight = _per_file_criticality(pr.files, criticality_by_path)
            churn = _calc_pr_churn_ratio(pr, author_prs[:idx], churn_window_days)
            code_score = eloc * c_factor * k_weight * (1 - churn)

            coverage_score = 100.0 * pr.coverage_delta
            perf_score = 100.0 * pr.performance_delta  # treat as percent improvements

            result[author] += code_score + coverage_score + perf_score

    # Reviews as collaboration impact
    for rv in reviews:
        pr = by_id.get(rv.pr_id)
        if pr is None:
            continue
        pr_eloc = sum(_effective_loc(f.added, f.deleted) for f in pr.files)
        influence = 1.5 * rv.suggestions_accepted + 0.25 * math.log1p(max(0.0, pr_eloc))
        result[rv.reviewer] += influence

    # Incident fixes reward
    for inc in incidents:
        result[inc.resolver] += float(max(1, min(5, inc.severity))) * 10.0

    return dict(result)


def compute_review_influence_score(
    reviews: Sequence[Review],
    prs_by_id: Mapping[int, PullRequest],
) -> dict[str, float]:
    """Compute a pure review influence score (RIS) per reviewer.

    Rewards actionable suggestions on larger PRs; independent of authorship.
    """
    scores: dict[str, float] = defaultdict(float)
    for rv in reviews:
        pr = prs_by_id.get(rv.pr_id)
        if pr is None:
            continue
        pr_eloc = sum(_effective_loc(f.added, f.deleted) for f in pr.files)
        score = 1.75 * rv.suggestions_accepted + 0.2 * math.log1p(max(0.0, pr_eloc))
        scores[rv.reviewer] += score
    return dict(scores)


__all__ = [
    "FileChange",
    "PullRequest",
    "Review",
    "IncidentFix",
    "compute_oaci",
    "compute_review_influence_score",
]

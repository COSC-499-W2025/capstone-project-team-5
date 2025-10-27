from __future__ import annotations

from datetime import UTC, datetime, timedelta

from capstone_project_team_5.services.contribution_metrics import (
    FileChange,
    IncidentFix,
    PullRequest,
    Review,
    compute_oaci,
    compute_review_influence_score,
)


def _dt(offset_days: int) -> datetime:
    return datetime.now(UTC) + timedelta(days=offset_days)


def test_compute_oaci_basic() -> None:
    prs = [
        PullRequest(
            pr_id=1,
            author="alice",
            merged=True,
            files=[FileChange("a/core.py", added=100, deleted=10, complexity_delta=-3)],
            coverage_delta=0.10,
            performance_delta=0.00,
            created_at=_dt(0),
        ),
        PullRequest(
            pr_id=2,
            author="bob",
            merged=True,
            files=[FileChange("b/util.py", added=50, deleted=5, complexity_delta=-1)],
            coverage_delta=0.00,
            performance_delta=0.05,
            created_at=_dt(1),
        ),
        PullRequest(
            pr_id=3,
            author="alice",
            merged=True,
            files=[FileChange("a/core.py", added=20, deleted=5, complexity_delta=1)],
            coverage_delta=0.00,
            performance_delta=0.00,
            created_at=_dt(7),
        ),
    ]

    reviews = [
        Review(pr_id=2, reviewer="alice", review_comments=4, suggestions_accepted=2),
        Review(pr_id=1, reviewer="bob", review_comments=2, suggestions_accepted=1),
    ]

    incidents = [
        IncidentFix(pr_id=4, resolver="alice", severity=3),
        IncidentFix(pr_id=5, resolver="bob", severity=1),
    ]

    crit = {"a/core.py": 1.8, "b/util.py": 1.0}

    scores = compute_oaci(prs, reviews, incidents, criticality_by_path=crit, churn_window_days=14)

    assert set(scores.keys()) == {"alice", "bob"}
    assert scores["alice"] > scores["bob"]


def test_compute_review_influence_score() -> None:
    pr1 = PullRequest(
        pr_id=10,
        author="x",
        merged=True,
        files=[FileChange("x.py", added=200, deleted=0)],
        created_at=_dt(0),
    )
    pr2 = PullRequest(
        pr_id=11,
        author="y",
        merged=True,
        files=[FileChange("y.py", added=10, deleted=0)],
        created_at=_dt(1),
    )
    reviews = [
        Review(pr_id=10, reviewer="alice", review_comments=5, suggestions_accepted=3),
        Review(pr_id=11, reviewer="bob", review_comments=2, suggestions_accepted=1),
    ]
    scores = compute_review_influence_score(reviews, {10: pr1, 11: pr2})
    assert scores["alice"] > scores["bob"]

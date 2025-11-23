"""
Utilities to select and summarize the top-ranked projects.

Provides two modes:
- DB-driven: read `Project.importance_rank` from the database and return
  the top N projects with full `ProjectSummary` data.
- Computed: accept a mapping of `project_id -> filesystem Path`, compute
  importance scores with `ContributionMetrics`, rank them, and return the
  top N entries (optionally enriched with DB `ProjectSummary` if available).

This module intentionally reuses `ProjectSummary` for per-project summaries
and `ContributionMetrics` for computing importance scores.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, select

from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.data.db import get_session
from outputs.project_summary import ProjectSummary


def _reflect_table(name: str, bind) -> Table:
    md = MetaData()
    return Table(name, md, autoload_with=bind)


def get_top_projects_from_db(n: int = 3) -> list[dict[str, Any]]:
    """Return top `n` projects by `importance_rank` from the DB.

    Each returned entry includes the `importance_rank` and the
    `ProjectSummary.summarize(...)` payload.
    """
    results: list[dict[str, Any]] = []
    with get_session() as session:
        engine = session.get_bind()
        project_tbl = _reflect_table("Project", engine)
        stmt = (
            select(project_tbl.c.name, project_tbl.c.importance_rank)
            .order_by(project_tbl.c.importance_rank.desc().nullslast())
            .limit(n)
        )

        rows = session.execute(stmt).mappings().all()
        for row in rows:
            name = row["name"]
            rank = row["importance_rank"]
            # reuse ProjectSummary to build the detailed summary
            try:
                summary = ProjectSummary.summarize(name)
            except ValueError:
                summary = {"project_name": name}

            results.append({"importance_rank": rank, "summary": summary})

    return results


def compute_top_projects_from_paths(paths: dict[int, Path], n: int = 3) -> list[dict[str, Any]]:
    """Compute importance scores for projects by filesystem analysis.

    Args:
        paths: Mapping of `project_id` -> `Path` to the project root on disk.
        n: Number of top projects to return.

    Returns:
        List of dictionaries with keys: `project_id`, `score`, `breakdown`,
        `metrics_source`, and optionally `summary` if the project exists in the DB.
    """
    scores: list[tuple[int, float, dict, str]] = []  # (pid, score, breakdown, source)

    for pid, root in paths.items():
        metrics, source = ContributionMetrics.get_project_contribution_metrics(root)
        duration, _ = ContributionMetrics.get_project_duration(root)

        # file_count: fallback to sum of metrics when available, else count files
        if metrics:
            file_count = int(sum(metrics.values()))
        else:
            file_count = sum(1 for f in root.rglob("*") if f.is_file())

        score, breakdown = ContributionMetrics.calculate_importance_score(
            metrics, duration, file_count
        )
        scores.append((pid, float(score), breakdown, source))

    # sort descending by score
    scores.sort(key=lambda t: t[1], reverse=True)

    top: list[dict[str, Any]] = []
    with get_session() as session:
        engine = session.get_bind()
        project_tbl = _reflect_table("Project", engine)

        for pid, score, breakdown, source in scores[:n]:
            entry: dict[str, Any] = {
                "project_id": pid,
                "score": score,
                "breakdown": breakdown,
                "metrics_source": source,
            }

            # Try to enrich with DB summary if project exists
            stmt = select(project_tbl.c.name).where(project_tbl.c.id == pid)
            res = session.execute(stmt).mappings().fetchone()
            if res is not None:
                try:
                    entry["summary"] = ProjectSummary.summarize(res["name"])  # type: ignore[arg-type]
                except ValueError:
                    entry["summary"] = {"project_id": pid}

            top.append(entry)

    return top


def display_top_projects(
    mode: str = "db", n: int = 3, paths: dict[int, Path] | None = None
) -> None:
    """Print the top projects as formatted JSON.

    mode: 'db' to use stored importance_rank, 'computed' to calculate scores from paths.
    """
    if mode == "db":
        out = get_top_projects_from_db(n=n)
    elif mode == "computed":
        if paths is None:
            raise ValueError("paths must be provided when mode='computed'")
        out = compute_top_projects_from_paths(paths, n=n)
    else:
        raise ValueError("mode must be 'db' or 'computed'")

    print(json.dumps(out, indent=2, default=str))

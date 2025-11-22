"""Service for calculating and storing project importance rankings."""

from __future__ import annotations

from capstone_project_team_5.contribution_metrics import ContributionMetrics
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project


def update_project_ranks(project_scores: list[tuple[str, str, float, dict[str, float]]]) -> None:
    """Update project importance ranks and scores in the database.

    Args:
        project_scores: List of (project_name, rel_path, score, breakdown) tuples.
    """
    with get_session() as session:
        project_data: list[tuple[int, float]] = []
        score_map: dict[int, float] = {}

        for name, rel_path, score, _breakdown in project_scores:
            project = (
                session.query(Project)
                .filter(Project.name == name, Project.rel_path == rel_path)
                .first()
            )
            if project:
                project_data.append((project.id, score))
                score_map[project.id] = score

        if not project_data:
            return

        ranked = ContributionMetrics.rank_projects(project_data)

        for project_id, rank in ranked:
            project = session.query(Project).filter(Project.id == project_id).first()
            if project:
                project.importance_rank = rank
                project.importance_score = score_map[project.id]

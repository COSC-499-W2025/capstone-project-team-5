"""
Output all key information for a project.
Author: Chris Hill
"""

import json
from typing import Any

from sqlalchemy import Table, MetaData, select, func
from sqlalchemy.orm import Session

from capstone_project_team_5.data.db import get_session


# Simple cache for reflected Table objects keyed by (engine id, table name).
_TABLE_CACHE: dict[tuple[int, str], Table] = {}


def _get_table(name: str, bind) -> Table:
    """Reflect and return a Table object for `name` using the given bind.

    Caches the Table per-engine to avoid repeated reflection overhead.
    """
    key = (id(bind), name)
    if key in _TABLE_CACHE:
        return _TABLE_CACHE[key]
    md = MetaData()
    tbl = Table(name, md, autoload_with=bind)
    _TABLE_CACHE[key] = tbl
    return tbl


class ProjectSummary:
    """Aggregate and output key information about a single project.

    This class provides helper query methods and an orchestrator method
    (`summarize`) that returns a structured dictionary containing project
    metadata, counts of artifacts and contributions, and associated skills.

    Methods are intentionally small to make unit testing straightforward.
    """

    @staticmethod
    def _get_connection():
        """Return the session context manager from the app DB wiring.

        This yields a SQLAlchemy Session when used as a context manager:
            with ProjectSummary._get_connection() as session:
                ...
        """
        return get_session()

    @classmethod
    def _get_project_metadata(cls, session: Session, project_name: str) -> dict[str, Any] | None:
        engine = session.get_bind()
        project_tbl = _get_table("Project", engine)
        stmt = select(
            project_tbl.c.id,
            project_tbl.c.name,
            project_tbl.c.description,
            project_tbl.c.is_collaborative,
            project_tbl.c.start_date,
            project_tbl.c.end_date,
            project_tbl.c.language,
            project_tbl.c.framework,
            project_tbl.c.importance_rank,
        ).where(project_tbl.c.name == project_name)

        res = session.execute(stmt)
        return res.mappings().fetchone()

    @classmethod
    def _get_artifact_counts(cls, session: Session, pid: int) -> dict[str, int]:
        engine = session.get_bind()
        artifact_tbl = _get_table("Artifact", engine)
        stmt = select(artifact_tbl.c.type, func.count().label("count")).where(
            artifact_tbl.c.project_id == pid
        ).group_by(artifact_tbl.c.type)
        res = session.execute(stmt)
        return {row["type"]: row["count"] for row in res.mappings().all()}

    @classmethod
    def _get_contrib_counts(cls, session: Session, pid: int) -> dict[str, int]:
        engine = session.get_bind()
        contrib_tbl = _get_table("Contribution", engine)
        stmt = select(
            contrib_tbl.c.activity_type, func.count().label("count")
        ).where(contrib_tbl.c.project_id == pid).group_by(contrib_tbl.c.activity_type)
        res = session.execute(stmt)
        return {row["activity_type"]: row["count"] for row in res.mappings().all()}

    @classmethod
    def _get_skills(cls, session: Session, pid: int) -> list[str]:
        engine = session.get_bind()
        skill_tbl = _get_table("Skill", engine)
        projectskill_tbl = _get_table("ProjectSkill", engine)
        stmt = select(skill_tbl.c.name).select_from(
            skill_tbl.join(projectskill_tbl, projectskill_tbl.c.skill_id == skill_tbl.c.id)
        ).where(projectskill_tbl.c.project_id == pid)
        res = session.execute(stmt)
        return [row["name"] for row in res.mappings().all()]

    @classmethod
    def summarize(cls, project_name: str) -> dict[str, Any]:
        """Return a structured summary for the given project name.

        This method orchestrates smaller helpers that execute individual
        queries. Splitting responsibilities improves readability and
        makes unit testing each database query easier.
        """
        with cls._get_connection() as session:
            project = cls._get_project_metadata(session, project_name)
            if project is None:
                raise ValueError(f"Project '{project_name}' not found in database.")

            pid = project["id"]
            artifact_counts = cls._get_artifact_counts(session, pid)
            contrib_counts = cls._get_contrib_counts(session, pid)
            skills = cls._get_skills(session, pid)

            summary: dict[str, Any] = {
                "project_name": project["name"],
                "description": project["description"],
                "collaboration": "collaborative" if project["is_collaborative"] else "individual",
                "language": project["language"],
                "framework": project["framework"],
                "importance_rank": project["importance_rank"],
                "start_date": project["start_date"],
                "end_date": project["end_date"],
                "activity_counts": contrib_counts,
                "artifact_counts": artifact_counts,
                "skills": skills,
                "summary": (
                    f"{project['name']} ({project['language'] or 'Unknown'}) using "
                    f"{project['framework'] or 'None'}, "
                    f"{'collaborative' if project['is_collaborative'] else 'individual'} project "
                    f"spanning {project['start_date']} to {project['end_date']}."
                ),
            }

            return summary

    @classmethod
    def display(cls, project_name: str) -> None:
        """Print the project summary as formatted JSON to stdout."""
        data = cls.summarize(project_name)
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    name = input("Enter project name: ").strip()
    try:
        ProjectSummary.display(name)
    except (ValueError, FileNotFoundError) as e:
        print("Error:", e)

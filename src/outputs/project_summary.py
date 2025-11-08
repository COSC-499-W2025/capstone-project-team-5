"""
Output all key information for a project.
Author: Chris Hill
"""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from capstone_project_team_5.data.db import get_session


class ProjectSummary:
    """Aggregate and output key information about a single project.

    This class provides helper query methods and an orchestrator method
    (`summarize`) that returns a structured dictionary containing project
    metadata, counts of artifacts and contributions, and associated skills.

    Methods are intentionally small to make unit testing straightforward.
    """

    @staticmethod
    def _get_connection() -> Session:
        """Return a SQLAlchemy Session context manager from the application.

        Use the shared `get_session()` to provide consistent session
        configuration (transactions, expire_on_commit, etc.). Callers should
        use this as a context manager: `with cls._get_connection() as session:`
        """
        return get_session()

    @classmethod
    def _get_project_metadata(cls, conn: Session, project_name: str) -> dict[str, Any] | None:
        project_sql = text(
            """
            SELECT id, name, description, is_collaborative, start_date, end_date,
                   language, framework, importance_rank
            FROM Project
            WHERE name = :name
            """
        )
        res = conn.execute(project_sql, {"name": project_name})
        return res.mappings().fetchone()

    @classmethod
    def _get_artifact_counts(cls, conn: Session, pid: int) -> dict[str, int]:
        artifacts_sql = text(
            """
            SELECT type, COUNT(*) AS count
            FROM Artifact
            WHERE project_id = :pid
            GROUP BY type
            """
        )
        res = conn.execute(artifacts_sql, {"pid": pid})
        return {row["type"]: row["count"] for row in res.mappings().all()}

    @classmethod
    def _get_contrib_counts(cls, conn: Session, pid: int) -> dict[str, int]:
        contrib_sql = text(
            """
            SELECT activity_type, COUNT(*) AS count
            FROM Contribution
            WHERE project_id = :pid
            GROUP BY activity_type
            """
        )
        res = conn.execute(contrib_sql, {"pid": pid})
        return {row["activity_type"]: row["count"] for row in res.mappings().all()}

    @classmethod
    def _get_skills(cls, conn: Session, pid: int) -> list[str]:
        skills_sql = text(
            """
            SELECT Skill.name
            FROM Skill
            JOIN ProjectSkill ON ProjectSkill.skill_id = Skill.id
            WHERE ProjectSkill.project_id = :pid
            """
        )
        res = conn.execute(skills_sql, {"pid": pid})
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

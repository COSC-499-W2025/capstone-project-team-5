"""
Output all key information for a project.
Author: Chris Hill
"""

import json
import os
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

# Database URL should be provided via the environment variable DATABASE_URL.
# Example values:
# - postgresql+psycopg2://user:pass@localhost/dbname
# - mysql+pymysql://user:pass@localhost/dbname
DB_ENV_VAR = "DATABASE_URL"
 

def _get_engine() -> Engine:
    """Return a SQLAlchemy Engine using the URL found in the environment.

    The database URL must be provided via the ``DATABASE_URL`` environment
    variable. This keeps the module backend-agnostic and avoids any direct
    references to a specific DB driver or file path.

    Raises:
        RuntimeError: if the environment variable is not set.
    """
    url = os.environ.get(DB_ENV_VAR)
    if not url:
        raise RuntimeError(
            f"Environment variable {DB_ENV_VAR} is not set. "
            "Set DATABASE_URL to your database connection URL (e.g. postgresql://...)."
        )
    return create_engine(url)


class ProjectSummary:
    """Aggregate and output key information about a single project.

    This class provides helper query methods and an orchestrator method
    (`summarize`) that returns a structured dictionary containing project
    metadata, counts of artifacts and contributions, and associated skills.

    Methods are intentionally small to make unit testing straightforward.
    """

    @staticmethod
    def _get_connection() -> Connection:
        """Return a SQLAlchemy Connection (Engine.connect()).

        The caller is responsible for closing the returned connection (it is
        typically used as a context manager).
        """
        engine = _get_engine()
        return engine.connect()

    @classmethod
    def _get_project_metadata(cls, conn: Connection, project_name: str) -> dict[str, Any] | None:
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
    def _get_artifact_counts(cls, conn: Connection, pid: int) -> dict[str, int]:
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
    def _get_contrib_counts(cls, conn: Connection, pid: int) -> dict[str, int]:
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
    def _get_skills(cls, conn: Connection, pid: int) -> list[str]:
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
        conn = cls._get_connection()
        try:
            project = cls._get_project_metadata(conn, project_name)
            if project is None:
                raise ValueError(f"Project '{project_name}' not found in database.")

            pid = project["id"]
            artifact_counts = cls._get_artifact_counts(conn, pid)
            contrib_counts = cls._get_contrib_counts(conn, pid)
            skills = cls._get_skills(conn, pid)

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
        finally:
            conn.close()

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

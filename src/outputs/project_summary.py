"""
Output all key information for a project.
Author: Chris Hill
"""

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "db" / "artifact_miner.db"


class ProjectSummary:

    """
    Aggregate and output key information about a single project.

    This class provides helper query methods and an orchestrator method
    (`summarize`) that returns a structured dictionary containing project
    metadata, counts of artifacts and contributions, and associated skills.

    Methods are intentionally small to make unit testing straightforward.
    """

    @staticmethod
    def _get_connection():
        """Open a DB connection and configure row factory.

        Returns:
            sqlite3.Connection: A connection to the configured `DB_PATH` with
                `row_factory` set to `sqlite3.Row`.

        Raises:
            FileNotFoundError: If the database file does not exist at `DB_PATH`.
        """
        if not DB_PATH.exists():
            raise FileNotFoundError(
                f"Database not found at {DB_PATH}. Ensure you have created artifact_miner.db inside the db/ folder."
            )
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _get_project_metadata(cur: sqlite3.Cursor, project_name: str) -> sqlite3.Row:
        """Fetch project metadata by project name.

        Args:
            cur (sqlite3.Cursor): Database cursor to use for the query.
            project_name (str): Exact name of the project to look up.

        Returns:
            sqlite3.Row: Row containing project metadata (id, name, description, ...).

        Raises:
            ValueError: If no project with `project_name` exists.
        """
        cur.execute(
            """
            SELECT id, name, description, is_collaborative, start_date, end_date,
                   language, framework, importance_rank
            FROM Project
            WHERE name = ?
            """,
            (project_name,),
        )
        project = cur.fetchone()
        if not project:
            raise ValueError(f"Project '{project_name}' not found in database.")
        return project

    @staticmethod
    def _get_artifact_counts(cur: sqlite3.Cursor, project_id: int) -> dict:
        """Return a mapping of artifact type to count for a given project.

        Args:
            cur (sqlite3.Cursor): Database cursor to use for the query.
            project_id (int): Project primary key.

        Returns:
            dict: Mapping of artifact type (str) to integer count.
        """
        cur.execute(
            """
            SELECT type, COUNT(*) AS count
            FROM Artifact
            WHERE project_id = ?
            GROUP BY type
            """,
            (project_id,),
        )
        return {row["type"]: row["count"] for row in cur.fetchall()}

    @staticmethod
    def _get_contrib_counts(cur: sqlite3.Cursor, project_id: int) -> dict:
        """Return a mapping of contribution activity type to count for a project.

        Args:
            cur (sqlite3.Cursor): Database cursor to use for the query.
            project_id (int): Project primary key.

        Returns:
            dict: Mapping of activity_type (str) to integer count.
        """
        cur.execute(
            """
            SELECT activity_type, COUNT(*) AS count
            FROM Contribution
            WHERE project_id = ?
            GROUP BY activity_type
            """,
            (project_id,),
        )
        return {row["activity_type"]: row["count"] for row in cur.fetchall()}

    @staticmethod
    def _get_skills(cur: sqlite3.Cursor, project_id: int) -> list:
        """Return a list of skill names associated with the project.

        Args:
            cur (sqlite3.Cursor): Database cursor to use for the query.
            project_id (int): Project primary key.

        Returns:
            list[str]: List of skill names (strings). Empty list if none.
        """
        cur.execute(
            """
            SELECT Skill.name
            FROM Skill
            JOIN ProjectSkill ON ProjectSkill.skill_id = Skill.id
            WHERE ProjectSkill.project_id = ?
            """,
            (project_id,),
        )
        return [row["name"] for row in cur.fetchall()]

    @staticmethod
    def summarize(project_name: str) -> dict:
        """Build and return a project summary dictionary.

        This orchestrates the helper query methods to produce a complete view of
        the project suitable for printing or serialization.

        Args:
            project_name (str): Exact name of the project to summarize.

        Returns:
            dict: A dictionary containing project metadata and derived metrics.
                Keys include: 'project_name', 'description', 'collaboration',
                'language', 'framework', 'importance_rank', 'start_date',
                'end_date', 'activity_counts', 'artifact_counts', 'skills',
                and 'summary' (a human-readable sentence).

        Raises:
            FileNotFoundError: If the database file is missing.
            ValueError: If the project is not found in the database.
        """
        conn = ProjectSummary._get_connection()
        try:
            cur = conn.cursor()
            project = ProjectSummary._get_project_metadata(cur, project_name)
            pid = project["id"]

            artifact_counts = ProjectSummary._get_artifact_counts(cur, pid)
            contrib_counts = ProjectSummary._get_contrib_counts(cur, pid)
            skills = ProjectSummary._get_skills(cur, pid)

            summary = {
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
    def display(cls, project_name: str):
        """Print the project summary as formatted JSON.

        Args:
            project_name (str): Exact name of the project to display.
        """
        data = cls.summarize(project_name)
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    name = input("Enter project name: ").strip()
    try:
        ProjectSummary.display(name)
    except (ValueError, FileNotFoundError) as e:
        print("Error:", e)

from datetime import datetime

from sqlalchemy.orm import Session

from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.user import User
from capstone_project_team_5.data.models.user_code_analysis import UserCodeAnalysis

"""Service for aggregating user skills across all projects."""


def get_chronological_skills(session: Session, user_id: int) -> list[dict]:
    """
    Gets all unique skills from the user's projects, sorted chronologically.

    :param session: SQLAlchemy session.
    :type session: Session
    :param user_id: User's id.
    :type user_id: int
    :return: List of the user's unique skills sorted by first usage.
    :rtype: list[dict]
    """

    user = session.get(User, user_id)

    if not user:
        return []

    skill_entries = {}

    # Use the link between users and their code analyses to get projects
    user_analyses = (
        session.query(UserCodeAnalysis).filter(UserCodeAnalysis.user_id == user_id).all()
    )

    for user_analysis in user_analyses:
        code_analysis = session.get(CodeAnalysis, user_analysis.analysis_id)

        if code_analysis and code_analysis.project:
            project = code_analysis.project

            for project_skill in project.project_skills:
                skill_key = (project_skill.skill.name, project_skill.skill.skill_type)

                # Only add to the list if not present or the skill has an earlier date
                if (
                    skill_key not in skill_entries
                    or project.created_at < skill_entries[skill_key]["first_used"]
                ):
                    skill_entries[skill_key] = {
                        "skill_name": project_skill.skill.name,
                        "skill_type": project_skill.skill.skill_type,
                        "first_used": project.created_at,
                    }

    skills = sorted(skill_entries.values(), key=lambda x: x["first_used"])

    return skills


def render_skills_as_markdown(skills: list[dict]) -> str:
    """
    Renders a list of skills as displayable markdown for the TUI.

    :param skills: List of skills to render.
    :type skills: list[dict]
    :return: String representation of the markdown.
    :rtype: str
    """

    if not skills:
        return "# Your Skills\n\nNo skills detected yet. Analyze a project first."

    tools = [s for s in skills if s["skill_type"] == SkillType.TOOL]
    practices = [s for s in skills if s["skill_type"] == SkillType.PRACTICE]

    parts: list[str] = ["# Your Skills\n"]

    if tools:
        parts.append("## Tools\n")

        for tool in tools:
            time: datetime = tool["first_used"]
            date_str: str = time.strftime("%b %Y")
            parts.append(f"- **{tool['skill_name']}** *(since {date_str})*")
        parts.append("")

    if practices:
        parts.append("## Practices\n")

        for practice in practices:
            time: datetime = practice["first_used"]
            date_str: str = time.strftime("%b %Y")
            parts.append(f"- **{practice['skill_name']}** *(since {date_str})*")
        parts.append("")

    parts.append(f"---\n*{len(tools)} {'tools' if len(tools) > 1 else 'tool'}, ")
    parts.append(f"{len(practices)} {'practices' if len(practices) > 1 else 'practice'}")
    parts.append(" detected across your projects.*")

    return "\n".join(parts)

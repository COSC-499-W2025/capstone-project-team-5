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


def format_skills_for_display(
    skills: list[dict], format_type: str, include_dates: bool = False
) -> str:
    """
    Formats the list of skills for user display.

    :param skills: List of skills to format.
    :type skills: list[dict]
    :param format_type: Either chronological or grouped.
    :type format_type: str
    :param include_dates: Whether to include dates in the output or not.
    :type include_dates: bool
    :return: Formatted string of skills.
    :rtype: str
    :raises: ValueError: If format type is invalid.
    """

    if not skills:
        return ""

    if format_type == "grouped":
        return _format_skills_grouped(skills, include_dates)
    elif format_type == "chronological":
        return _format_skills_chronological(skills, include_dates)
    else:
        raise ValueError("Invalid format type.")


def _format_skills_grouped(skills: list[dict], include_dates: bool) -> str:
    """
    Formats skills grouped by skill type.
    """

    tools = [s for s in skills if s["skill_type"] == SkillType.TOOL]
    practices = [s for s in skills if s["skill_type"] == SkillType.PRACTICE]

    output = []

    if tools:
        output.append("Tools:")

        for skill in tools:
            if include_dates:
                date_str = _format_date(skill["first_used"])
                output.append(f"  - {skill['skill_name']} ({date_str})")
            else:
                output.append(f"  - {skill['skill_name']}")
    if practices:
        if tools:
            output.append("")
        output.append("Practices:")

        for skill in practices:
            if include_dates:
                date_str = _format_date(skill["first_used"])
                output.append(f"  - {skill['skill_name']} ({date_str})")
            else:
                output.append(f"  - {skill['skill_name']}")

    return "\n".join(output)


def _format_skills_chronological(skills: list[dict], include_dates: bool) -> str:
    """Formats skills in chronological order."""

    output = ["Skills:"]

    for skill in skills:
        type_indicator = "[Tool]" if skill["skill_type"] == SkillType.TOOL else "[Practice]"

        if include_dates:
            date_str = _format_date(skill["first_used"])
            output.append(f"- {type_indicator} {skill['skill_name']} ({date_str})")
        else:
            output.append(f"{type_indicator} {skill['skill_name']}")

    return "\n".join(output)


def _format_date(dt: datetime) -> str:
    """
    Format datetime for display.
    """

    return dt.strftime("%b %Y")

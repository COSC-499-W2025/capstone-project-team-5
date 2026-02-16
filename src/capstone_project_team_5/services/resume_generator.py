"""Resume generation service.

Pulls user data from DB services into a ResumeData dict
and renders it with a pluggable LaTeX template.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import Project, User
from capstone_project_team_5.services.education import get_educations
from capstone_project_team_5.services.resume import get_all_resumes
from capstone_project_team_5.services.user_profile import get_user_profile
from capstone_project_team_5.services.user_skill_list import get_chronological_skills
from capstone_project_team_5.services.work_experience import get_work_experiences
from capstone_project_team_5.templates import get_template

if TYPE_CHECKING:
    from capstone_project_team_5.services.resume_data import (
        ResumeContactInfo,
        ResumeData,
        ResumeEducationEntry,
        ResumeProjectEntry,
        ResumeSkills,
        ResumeWorkEntry,
    )

__all__ = [
    "aggregate_resume_data",
    "generate_resume_files",
    "generate_resume_pdf",
    "generate_resume_tex",
]


# -----------------------------------------------------------------------
# Internal builders


def _build_contact(profile: dict) -> ResumeContactInfo:
    """Map a user-profile dict to :class:`ResumeContactInfo`."""
    first = profile.get("first_name") or ""
    last = profile.get("last_name") or ""
    name = f"{first} {last}".strip()

    contact: ResumeContactInfo = {"name": name}

    email = profile.get("email")
    if email:
        contact["email"] = email
    phone = profile.get("phone")
    if phone:
        contact["phone"] = phone
    linkedin = profile.get("linkedin_url")
    if linkedin:
        contact["linkedin_url"] = linkedin
    github = profile.get("github_username")
    if github:
        contact["github_url"] = f"https://github.com/{github}"
    website = profile.get("website")
    if website:
        contact["website_url"] = website

    return contact


def _build_education_list(
    educations: list[dict],
) -> list[ResumeEducationEntry]:
    """Map service education dicts to resume entries."""
    result: list[ResumeEducationEntry] = []
    for edu in educations:
        entry: ResumeEducationEntry = {
            "institution": edu.get("institution", ""),
            "degree": edu.get("degree", ""),
        }
        field = edu.get("field_of_study")
        if field:
            entry["field_of_study"] = field
        location = edu.get("location")
        if location:
            entry["location"] = location
        start = edu.get("start_date")
        if start:
            entry["start_date"] = str(start)
        end = edu.get("end_date")
        if end:
            entry["end_date"] = str(end)
        if edu.get("is_current"):
            entry["is_current"] = True
        gpa = edu.get("gpa")
        if gpa is not None:
            entry["gpa"] = gpa

        # achievements is stored as a JSON string
        raw_achievements = edu.get("achievements")
        if raw_achievements:
            if isinstance(raw_achievements, str):
                try:
                    parsed = json.loads(raw_achievements)
                    if isinstance(parsed, list):
                        entry["achievements"] = [str(a) for a in parsed]
                except (json.JSONDecodeError, TypeError):
                    entry["achievements"] = [raw_achievements]
            elif isinstance(raw_achievements, list):
                entry["achievements"] = [str(a) for a in raw_achievements]

        result.append(entry)
    return result


def _build_work_list(
    work_experiences: list[dict],
) -> list[ResumeWorkEntry]:
    """Map service work-experience dicts to resume entries."""
    result: list[ResumeWorkEntry] = []
    for work in work_experiences:
        entry: ResumeWorkEntry = {
            "company": work.get("company", ""),
            "title": work.get("title", ""),
        }
        location = work.get("location")
        if location:
            entry["location"] = location
        start = work.get("start_date")
        if start:
            entry["start_date"] = str(start)
        end = work.get("end_date")
        if end:
            entry["end_date"] = str(end)
        if work.get("is_current"):
            entry["is_current"] = True

        # bullets is stored as a JSON string
        raw_bullets = work.get("bullets")
        if raw_bullets:
            if isinstance(raw_bullets, str):
                try:
                    parsed = json.loads(raw_bullets)
                    if isinstance(parsed, list):
                        entry["bullets"] = [str(b) for b in parsed]
                except (json.JSONDecodeError, TypeError):
                    entry["bullets"] = [raw_bullets]
            elif isinstance(raw_bullets, list):
                entry["bullets"] = [str(b) for b in raw_bullets]

        result.append(entry)
    return result


def _build_project_list(
    resumes: list[dict],
    project_dates: dict[int, dict],
) -> list[ResumeProjectEntry]:
    """Map resume-project dicts to resume entries."""
    result: list[ResumeProjectEntry] = []
    for rp in resumes:
        entry: ResumeProjectEntry = {
            "name": rp.get("project_name") or rp.get("title", ""),
        }
        desc = rp.get("description")
        if desc:
            entry["description"] = desc

        bullets = rp.get("bullet_points", [])
        if bullets:
            entry["bullets"] = bullets

        # Technologies from analysis_snapshot
        snapshot = rp.get("analysis_snapshot", [])
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except (json.JSONDecodeError, TypeError):
                snapshot = []
        if snapshot and isinstance(snapshot, list):
            entry["technologies"] = [str(t) for t in snapshot]

        # Project URL / dates from the Project model
        pid = rp.get("project_id")
        if pid and pid in project_dates:
            pinfo = project_dates[pid]
            start = pinfo.get("start_date")
            if start:
                entry["start_date"] = str(start)
            end = pinfo.get("end_date")
            if end:
                entry["end_date"] = str(end)

        result.append(entry)
    return result


def _build_skills(skill_list: list[dict]) -> ResumeSkills:
    """Split chronological skills into tools and practices."""
    tools: list[str] = []
    practices: list[str] = []
    for skill in skill_list:
        stype = skill.get("skill_type")
        sname = skill.get("skill_name", "")
        if stype == SkillType.TOOL:
            tools.append(sname)
        elif stype == SkillType.PRACTICE:
            practices.append(sname)
    return {"tools": tools, "practices": practices}


def _fetch_project_dates(
    project_ids: list[int],
) -> dict[int, dict]:
    """Query :class:`Project` rows for start/end dates.

    Returns a mapping ``{project_id: {"start_date": ..., "end_date": ...}}``.
    """
    if not project_ids:
        return {}

    result: dict[int, dict] = {}
    try:
        with get_session() as session:
            projects = session.query(Project).filter(Project.id.in_(project_ids)).all()
            for p in projects:
                result[p.id] = {
                    "start_date": p.start_date,
                    "end_date": p.end_date,
                }
    except Exception:
        raise
    return result


# -----------------------------------------------------------------------
# Public API


def aggregate_resume_data(
    username: str,
) -> ResumeData | None:
    """Fetch and assemble all data needed to render a resume.

    Args:
        username: Target user.

    Returns:
        A filled :class:`ResumeData` dict, or *None* if the user has no
        profile.
    """
    try:
        profile = get_user_profile(username)
        if profile is None:
            return None

        contact = _build_contact(profile)

        educations = get_educations(username) or []
        education_entries = _build_education_list(educations)

        work_exps = get_work_experiences(username) or []
        work_entries = _build_work_list(work_exps)

        resumes = get_all_resumes(username) or []
        project_ids = [rp["project_id"] for rp in resumes if rp.get("project_id")]
        project_dates = _fetch_project_dates(project_ids)
        project_entries = _build_project_list(resumes, project_dates)

        # Skills require a raw session + user_id
        skills: ResumeSkills = {"tools": [], "practices": []}
        with get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user:
                raw_skills = get_chronological_skills(session, user.id)
                skills = _build_skills(raw_skills)

        data: ResumeData = {
            "contact": contact,
            "education": education_entries,
            "work_experience": work_entries,
            "projects": project_entries,
            "skills": skills,
        }
        return data

    except Exception:
        raise


def generate_resume_tex(
    username: str,
    template_name: str = "jake",
) -> str | None:
    """Generate the LaTeX source for a resume.

    Args:
        username: Target user.
        template_name: Registered template identifier.

    Returns:
        The full ``.tex`` source as a string, or *None* on failure.
    """
    try:
        resume_data = aggregate_resume_data(username)
        if resume_data is None:
            return None

        template = get_template(template_name)
        doc = template.build(resume_data)
        return doc.dumps()

    except Exception:
        raise


def generate_resume_pdf(
    username: str,
    output_path: Path,
    template_name: str = "jake",
    *,
    compiler: str = "pdflatex",
) -> Path | None:
    """Generate a PDF resume via LaTeX compilation.

    Requires *compiler* (``pdflatex`` or ``latexmk``) to be installed
    on the system.

    Args:
        username: Target user.
        output_path: Desired output file path **without** extension.
        template_name: Registered template identifier.
        compiler: LaTeX compiler to invoke.

    Returns:
        The ``Path`` of the generated ``.pdf``, or *None* on failure.
    """
    try:
        resume_data = aggregate_resume_data(username)
        if resume_data is None:
            return None

        template = get_template(template_name)
        doc = template.build(resume_data)

        # PyLaTeX appends .pdf/.tex automatically
        doc.generate_pdf(
            str(output_path),
            clean_tex=False,
            compiler=compiler,
        )
        return Path(f"{output_path}.pdf")

    except Exception:
        raise


def generate_resume_files(
    username: str,
    output_dir: Path,
    template_name: str = "jake",
    *,
    compiler: str = "pdflatex",
) -> dict[str, Path] | None:
    """Generate both ``.tex`` and ``.pdf`` files.

    Args:
        username: Target user.
        output_dir: Directory to write files into.
        template_name: Registered template identifier.
        compiler: LaTeX compiler to invoke.

    Returns:
        ``{"tex": Path, "pdf": Path}`` on success, or *None* on failure.
    """
    try:
        resume_data = aggregate_resume_data(username)
        if resume_data is None:
            return None

        template = get_template(template_name)
        doc = template.build(resume_data)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = output_dir / f"{username}_resume"

        doc.generate_pdf(
            str(stem),
            clean_tex=False,
            compiler=compiler,
        )

        return {
            "tex": Path(f"{stem}.tex"),
            "pdf": Path(f"{stem}.pdf"),
        }

    except Exception:
        raise

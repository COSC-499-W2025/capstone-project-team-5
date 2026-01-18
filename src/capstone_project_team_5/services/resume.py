import json
from datetime import UTC, datetime

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models.project import Project
from capstone_project_team_5.data.models.resume import Resume, ResumeBulletPoint, ResumeProject
from capstone_project_team_5.data.models.user import User


def save_resume(
    username: str,
    project_id: int,
    title: str,
    description: str,
    bullet_points: list[str],
    analysis_snapshot: list[str],
) -> bool:
    """
    Saves a resume item to the database or updates
    an existing item if one already exists for the project.

    Args:
        username: The username of the resume owner
        project_id: The ID of the project to create a resume for
        title: Custom title for the resume project
        description: Custom description (e.g., "Python Flask Web App")
        bullet_points: List of resume bullet point strings
        analysis_snapshot: List of skills/tools/practices to snapshot

    Returns:
        True if save was successful, False otherwise
    """

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()

        if not user:
            return False

        project = session.query(Project).filter(Project.id == project_id).first()

        if not project:
            return False

        resume = session.query(Resume).filter(Resume.user_id == user.id).first()

        if not resume:
            resume = Resume(user_id=user.id, name="My Resume")
            session.add(resume)
            session.flush()

        resume_project = (
            session.query(ResumeProject)
            .filter(ResumeProject.resume_id == resume.id, ResumeProject.project_id == project_id)
            .first()
        )

        snapshot_json = json.dumps(analysis_snapshot) if analysis_snapshot else None

        if resume_project:
            # Update existing
            resume_project.title = title
            resume_project.description = description
            resume_project.analysis_snapshot = snapshot_json
            resume_project.updated_at = datetime.now(UTC)

            # Delete old bullets
            for bullet in resume_project.bullet_points:
                session.delete(bullet)
            session.flush()
        else:
            # Create new
            resume_project = ResumeProject(
                resume_id=resume.id,
                project_id=project_id,
                title=title,
                description=description,
                analysis_snapshot=snapshot_json,
            )
            session.add(resume_project)
            session.flush()

        # Add new bullet points
        for content in bullet_points:
            bullet = ResumeBulletPoint(resume_project_id=resume_project.id, content=content)
            session.add(bullet)

        resume.updated_at = datetime.now(UTC)

        session.commit()

        return True


def get_resume(username: str, project_id: int) -> dict | None:
    """
    Retrieves a resume from the database returning it as a dict
    or None if none is found.

    Args:
        username: The username of the resume owner
        project_id: The ID of the project

    Returns:
        Dictionary containing resume data with structure:
        {
            "id": int,
            "resume_id": int,
            "project_id": int,
            "project_name": str,
            "rel_path": str,
            "title": str | None,
            "description": str | None,
            "analysis_snapshot": list[str],
            "bullet_points": list[str],
            "created_at": datetime,
            "updated_at": datetime
        }
        Returns None if resume not found
    """

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()

        if not user:
            return None

        resume_project = (
            session.query(ResumeProject)
            .join(Resume)
            .join(Project)
            .filter(Resume.user_id == user.id, ResumeProject.project_id == project_id)
            .first()
        )

        if not resume_project:
            return None

        snapshot = []

        if resume_project.analysis_snapshot:
            try:
                snapshot = json.loads(resume_project.analysis_snapshot)
            except (json.JSONDecodeError, TypeError):
                snapshot = []

        bullets = [bp.content for bp in resume_project.bullet_points]

        return {
            "id": resume_project.id,
            "resume_id": resume_project.resume_id,
            "project_id": resume_project.project_id,
            "project_name": resume_project.project.name,
            "rel_path": resume_project.project.rel_path,
            "title": resume_project.title,
            "description": resume_project.description,
            "analysis_snapshot": snapshot,
            "bullet_points": bullets,
            "created_at": resume_project.created_at,
            "updated_at": resume_project.updated_at,
        }


def delete_resume(username: str, project_id: int) -> bool:
    """
    Deletes a resume from the database returning
    if the operation was successful.

    Args:
        username: The username of the resume owner
        project_id: The ID of the project

    Returns:
        True if deletion was successful, False if resume not found or error occurred
    """

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()

        if not user:
            return False

        resume_project = (
            session.query(ResumeProject)
            .join(Resume)
            .filter(Resume.user_id == user.id, ResumeProject.project_id == project_id)
            .first()
        )

        if not resume_project:
            return False

        session.delete(resume_project)

        resume = resume_project.resume
        resume.updated_at = datetime.now(UTC)

        session.commit()

        return True


def get_all_resumes(username: str) -> list[dict]:
    """
    Get all resume projects for a user.

    Args:
        username: The username of the resume owner

    Returns:
        List of resume project dictionaries
    """

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()

        if not user:
            return []

        resume_projects = (
            session.query(ResumeProject)
            .join(Resume)
            .join(Project)
            .filter(Resume.user_id == user.id)
            .order_by(ResumeProject.updated_at.desc())
            .all()
        )

        results = []
        for rp in resume_projects:
            snapshot = []
            if rp.analysis_snapshot:
                try:
                    snapshot = json.loads(rp.analysis_snapshot)
                except (json.JSONDecodeError, TypeError):
                    snapshot = []

            results.append(
                {
                    "id": rp.id,
                    "resume_id": rp.resume_id,
                    "project_id": rp.project_id,
                    "project_name": rp.project.name,
                    "rel_path": rp.project.rel_path,
                    "title": rp.title,
                    "description": rp.description,
                    "analysis_snapshot": snapshot,
                    "bullet_points": [bp.content for bp in rp.bullet_points],
                    "created_at": rp.created_at,
                    "updated_at": rp.updated_at,
                }
            )

        return results


def update_resume_bullets(username: str, project_id: int, bullet_points: list[str]) -> bool:
    """
    Update only the bullet points for an existing resume project.

    Args:
        username: The username of the resume owner
        project_id: The ID of the project
        bullet_points: New list of bullet point strings

    Returns:
        True if update was successful, False otherwise
    """

    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            return False

        resume_project = (
            session.query(ResumeProject)
            .join(Resume)
            .filter(Resume.user_id == user.id, ResumeProject.project_id == project_id)
            .first()
        )

        if not resume_project:
            return False

        # Delete existing bullets
        for bullet in resume_project.bullet_points:
            session.delete(bullet)
        session.flush()

        # Add new bullets
        for content in bullet_points:
            bullet = ResumeBulletPoint(resume_project_id=resume_project.id, content=content)
            session.add(bullet)

        resume_project.updated_at = datetime.now(UTC)
        resume_project.resume.updated_at = datetime.now(UTC)

        session.commit()
        return True

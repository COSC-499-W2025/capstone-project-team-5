"""ORM models package for database tables.

This package provides SQLAlchemy ORM models representing database tables:
- ConsentRecord: User consent decisions and configuration
- UploadRecord: Metadata for processed zip file uploads
- Project: Discovered projects within uploaded ZIP archives
- ArtifactSource: Tracks which uploads contributed artifacts to projects
- PortfolioItem: Generated portfolio entries and reports
- CodeAnalysis: Language-specific code analysis results
- Skill: Detected skills (tools and practices)
- ProjectSkill: Many-to-many association between projects and skills
- UserProfile: User contact and personal information
- Education: User educational history
- WorkExperience: User work history

All models inherit from the shared Base declarative class defined in data.db.
"""

from capstone_project_team_5.data.db import Base
from capstone_project_team_5.data.models.artifact_source import ArtifactSource
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.consent_record import ConsentRecord
from capstone_project_team_5.data.models.education import Education
from capstone_project_team_5.data.models.portfolio import Portfolio
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem
from capstone_project_team_5.data.models.project import Project
from capstone_project_team_5.data.models.skill import ProjectSkill, Skill
from capstone_project_team_5.data.models.upload_record import UploadRecord
from capstone_project_team_5.data.models.user import User
from capstone_project_team_5.data.models.user_code_analysis import UserCodeAnalysis
from capstone_project_team_5.data.models.user_profile import UserProfile
from capstone_project_team_5.data.models.work_experience import WorkExperience

__all__ = [
    "Base",
    "ArtifactSource",
    "CodeAnalysis",
    "ConsentRecord",
    "Education",
    "Portfolio",
    "PortfolioItem",
    "Project",
    "ProjectSkill",
    "Skill",
    "UploadRecord",
    "User",
    "UserCodeAnalysis",
    "UserProfile",
    "WorkExperience",
]

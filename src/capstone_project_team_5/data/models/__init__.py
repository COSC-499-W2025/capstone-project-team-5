"""ORM models package for database tables.

This package provides SQLAlchemy ORM models representing database tables:
- ConsentRecord: User consent decisions and configuration
- UploadRecord: Metadata for processed zip file uploads
- Project: Discovered projects within uploaded ZIP archives
- PortfolioItem: Generated portfolio entries and reports
- CodeAnalysis: Language-specific code analysis results

All models inherit from the shared Base declarative class defined in data.db.
"""

from capstone_project_team_5.data.db import Base
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.consent_record import ConsentRecord
from capstone_project_team_5.data.models.portfolio_item import PortfolioItem
from capstone_project_team_5.data.models.project import Project
from capstone_project_team_5.data.models.upload_record import UploadRecord

__all__ = ["Base", "CodeAnalysis", "ConsentRecord", "PortfolioItem", "Project", "UploadRecord"]

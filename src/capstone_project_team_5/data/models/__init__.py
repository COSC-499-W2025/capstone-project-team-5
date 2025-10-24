"""ORM models package for database tables.

This package provides SQLAlchemy ORM models representing database tables:
- ConsentRecord: User consent decisions and configuration
- UploadRecord: Metadata for processed zip file uploads

All models inherit from the shared Base declarative class defined in data.db.
"""

from capstone_project_team_5.data.db import Base
from capstone_project_team_5.data.models.consent_record import ConsentRecord
from capstone_project_team_5.data.models.upload_record import UploadRecord

__all__ = ["Base", "ConsentRecord", "UploadRecord"]

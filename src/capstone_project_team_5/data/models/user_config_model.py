from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Boolean, JSON, DateTime
from datetime import datetime, timezone

Base = declarative_base()

class UserConfigModel(Base):
    __tablename__ = "UserConfig"

    id = Column(Integer, primary_key=True, default=1)
    consent_given = Column(Boolean, nullable=False, default=False)
    use_external_services = Column(Boolean, nullable=False, default=False)
    external_services = Column(JSON, default=dict)
    default_ignore_patterns = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), on_update=lambda: datetime.now(timezone.utc))
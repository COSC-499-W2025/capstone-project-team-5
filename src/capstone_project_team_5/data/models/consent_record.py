"""ORM model for storing user consent decisions and configuration.

This module defines the ConsentRecord table that captures user permissions
for file access, external service integration, and related configuration
preferences collected during the consent flow.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from capstone_project_team_5.data.db import Base


class ConsentRecord(Base):
    """Persisted representation of a user's consent configuration.

    Attributes:
        id: Auto-incrementing primary key.
        consent_given: Whether the user agreed to main file access consent.
        use_external_services: Whether the user agreed to external service integration.
        external_services: JSON mapping of service names to enabled status.
        default_ignore_patterns: JSON list of file/folder patterns to ignore during analysis.
        created_at: UTC timestamp of when the consent was recorded.
    """

    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    use_external_services: Mapped[bool] = mapped_column(Boolean, nullable=False)
    external_services: Mapped[dict[str, bool]] = mapped_column(JSON, nullable=False, default=dict)
    default_ignore_patterns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

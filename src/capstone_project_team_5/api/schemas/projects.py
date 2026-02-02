"""Pydantic schemas for project API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, confloat


class ProjectSummary(BaseModel):
    """Public-facing project summary for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rel_path: str
    file_count: int
    has_git_repo: bool
    is_collaborative: bool
    is_showcase: bool
    has_thumbnail: bool
    thumbnail_url: str | None
    importance_rank: int | None
    importance_score: float | None
    user_role: str | None
    user_contribution_percentage: confloat(ge=0, le=100) | None
    created_at: datetime
    updated_at: datetime


class ProjectUploadResponse(BaseModel):
    """Response schema for zip upload endpoint."""

    upload_id: int
    filename: str
    size_bytes: int
    file_count: int
    created_at: datetime
    projects: list[ProjectSummary]


class ProjectUpdateRequest(BaseModel):
    """Fields allowed to be updated for a project."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    rel_path: str | None = None
    importance_rank: int | None = None
    importance_score: float | None = None
    user_role: str | None = None
    user_contribution_percentage: confloat(ge=0, le=100) | None = None
    is_showcase: bool | None = None


class CollaboratorsRaw(BaseModel):
    """Raw collaborator summary."""

    count: int
    identities: list[str]


class FileSummary(BaseModel):
    """Summary of files in the analyzed project."""

    total_files: int
    total_size: str
    total_size_bytes: int


class ContributionData(BaseModel):
    """Contribution metrics and source."""

    metrics: dict[str, int]
    source: str


class GitContribution(BaseModel):
    """Git contribution statistics."""

    commits: int
    added: int
    deleted: int


class GitAuthorContribution(BaseModel):
    """Contribution details for a specific author."""

    author: str
    commits: int
    added: int
    deleted: int


class GitSummary(BaseModel):
    """Git-related summary for a project."""

    is_repo: bool
    current_author: str | None
    author_contributions: list[GitAuthorContribution]
    current_author_contribution: GitContribution | None
    activity_chart: list[str]


class SkillTimelineEntry(BaseModel):
    """First-seen timeline entry for a skill."""

    date: str
    skills: list[str]


class ProjectAnalysisResult(BaseModel):
    """Structured analysis result for a project."""

    id: int
    name: str
    rel_path: str
    language: str
    framework: str | None
    other_languages: list[str]
    practices: list[str]
    tools: list[str]
    duration: str
    collaborators_display: str
    collaborators_raw: CollaboratorsRaw
    file_summary: FileSummary
    contribution: ContributionData
    contribution_summary: str
    importance_score: float
    score_breakdown: dict[str, float]
    ai_bullets: list[str]
    ai_warning: str | None
    resume_bullets: list[str]
    resume_bullet_source: str
    skill_timeline: list[SkillTimelineEntry]
    git: GitSummary
    user_role: str | None
    user_contribution_percentage: confloat(ge=0, le=100) | None


class ProjectAnalysisSkipped(BaseModel):
    """Skipped project in analyze-all flow."""

    project_id: int
    reason: str


class ProjectsAnalyzeAllResponse(BaseModel):
    """Response schema for analyze-all endpoint."""

    analyzed: list[ProjectAnalysisResult]
    skipped: list[ProjectAnalysisSkipped]

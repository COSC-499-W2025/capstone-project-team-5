"""Template-agnostic data contracts for resume generation.

These TypedDicts define the shape of data that flows from the aggregation
layer to every resume template.  Templates depend ONLY on these
contracts (not ORM) so the data-fetching logic can evolve
independently.
"""

from __future__ import annotations

from typing import TypedDict

__all__ = [
    "ResumeContactInfo",
    "ResumeData",
    "ResumeEducationEntry",
    "ResumeProjectEntry",
    "ResumeSkills",
    "ResumeWorkEntry",
]


class ResumeContactInfo(TypedDict, total=False):
    """User name and contact links shown in the resume header."""

    name: str
    email: str
    phone: str
    linkedin_url: str
    github_url: str
    website_url: str


class ResumeEducationEntry(TypedDict, total=False):
    """A single education record."""

    institution: str
    degree: str
    field_of_study: str
    location: str
    start_date: str  # ISO date string or human-readable
    end_date: str
    is_current: bool
    gpa: float
    achievements: list[str]


class ResumeWorkEntry(TypedDict, total=False):
    """A single work-experience record."""

    company: str
    title: str
    location: str
    start_date: str
    end_date: str
    is_current: bool
    bullets: list[str]


class ResumeProjectEntry(TypedDict, total=False):
    """A single project record."""

    name: str
    description: str
    bullets: list[str]
    technologies: list[str]
    url: str
    start_date: str
    end_date: str


class ResumeSkills(TypedDict, total=False):
    """Skill lists split by category."""

    tools: list[str]
    practices: list[str]


class ResumeData(TypedDict, total=False):
    """Top-level bundle passed to every template's ``build()`` method."""

    contact: ResumeContactInfo
    education: list[ResumeEducationEntry]
    work_experience: list[ResumeWorkEntry]
    projects: list[ResumeProjectEntry]
    skills: ResumeSkills

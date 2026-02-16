"""Tests for the resume generation pipeline.

Covers:
- Template registry
- Template helpers (escape_latex, format_date_range, _strip_protocol)
- Jake template rendering
- Data builders (_build_contact, _build_education_list, etc.)
- Project-date fetching
- Top-level aggregation & generation functions
"""

from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.models import Base, Project, User
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.education import Education
from capstone_project_team_5.data.models.resume import Resume, ResumeProject
from capstone_project_team_5.data.models.skill import ProjectSkill, Skill
from capstone_project_team_5.data.models.upload_record import UploadRecord
from capstone_project_team_5.data.models.user_code_analysis import UserCodeAnalysis
from capstone_project_team_5.data.models.user_profile import UserProfile
from capstone_project_team_5.data.models.work_experience import WorkExperience

# ---------------------------------------------------------------------------
# Fixtures

USERNAME = "testuser"


@pytest.fixture(scope="function")
def tmp_db(monkeypatch, tmp_path):
    """Spin up a throw-away SQLite database."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", sessionmaker(bind=engine))
    yield
    engine.dispose()


@pytest.fixture()
def seeded(tmp_db):
    """Create a user with profile, education, work, project+resume, skills."""
    with db_module.get_session() as s:
        user = User(username=USERNAME, password_hash="hash")
        s.add(user)
        s.flush()

        # Profile
        profile = UserProfile(
            user_id=user.id,
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="555-0100",
            linkedin_url="https://linkedin.com/in/testuser",
            github_username="testuser",
            website="https://testuser.dev",
        )
        s.add(profile)

        # Education
        edu = Education(
            user_id=user.id,
            institution="State University",
            degree="B.S.",
            field_of_study="Computer Science",
            start_date=date(2018, 8, 15),
            end_date=date(2022, 5, 15),
            gpa=3.85,
            achievements=json.dumps(["Dean's List", "Summa Cum Laude"]),
        )
        s.add(edu)

        # Work experience
        work = WorkExperience(
            user_id=user.id,
            company="Acme Corp",
            title="Software Engineer Intern",
            location="San Francisco, CA",
            start_date=date(2021, 6, 1),
            end_date=date(2021, 8, 31),
            bullets=json.dumps(["Built REST APIs", "Reduced latency by 30%"]),
        )
        s.add(work)

        # Upload → Project → Resume → ResumeProject
        upload = UploadRecord(filename="z.zip", size_bytes=999, file_count=5)
        s.add(upload)
        s.flush()

        project = Project(
            upload_id=upload.id,
            name="Cool Project",
            rel_path="cool_project",
            has_git_repo=False,
            file_count=5,
            is_collaborative=False,
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2022, 6, 1),
        )
        s.add(project)
        s.flush()

        resume = Resume(user_id=user.id, name="My Resume")
        s.add(resume)
        s.flush()

        rp = ResumeProject(
            resume_id=resume.id,
            project_id=project.id,
            title="Cool Project",
            description="A cool project",
            analysis_snapshot=json.dumps(["Python", "Flask"]),
        )
        s.add(rp)

        # Skills (via CodeAnalysis → UserCodeAnalysis → ProjectSkill)
        analysis = CodeAnalysis(
            project_id=project.id,
            language="python",
            metrics_json="{}",
        )
        s.add(analysis)
        s.flush()

        uca = UserCodeAnalysis(user_id=user.id, analysis_id=analysis.id)
        s.add(uca)

        skill_py = Skill(name="Python", skill_type=SkillType.TOOL)
        skill_tdd = Skill(name="TDD", skill_type=SkillType.PRACTICE)
        s.add_all([skill_py, skill_tdd])
        s.flush()

        s.add(ProjectSkill(project_id=project.id, skill_id=skill_py.id))
        s.add(ProjectSkill(project_id=project.id, skill_id=skill_tdd.id))

        s.commit()
        return USERNAME


# ======================================================================
# Template Registry
# ======================================================================


class TestTemplateRegistry:
    def test_get_jake(self):
        from capstone_project_team_5.templates import get_template

        t = get_template("jake")
        assert t.name == "Jake's Resume"

    def test_unknown_raises(self):
        from capstone_project_team_5.templates import get_template

        with pytest.raises(ValueError, match="Unknown template"):
            get_template("nonexistent")


# ======================================================================
# Template Helpers


class TestTemplateHelpers:
    """Tests for ResumeTemplate static helpers and JakeResumeTemplate._strip_protocol."""

    def _template(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        return JakeResumeTemplate()

    def test_escape_ampersand(self):
        assert self._template().escape_latex("A & B") == r"A \& B"

    def test_escape_percent(self):
        assert self._template().escape_latex("100%") == r"100\%"

    def test_escape_underscore(self):
        assert self._template().escape_latex("my_var") == r"my\_var"

    # -- format_date_range -------------------------------------------------

    def test_format_full_range(self):
        t = self._template()
        result = t.format_date_range("2018-08-15", "2022-05-15")
        assert result == "Aug. 2018 -- May 2022"

    def test_format_current(self):
        t = self._template()
        result = t.format_date_range("2021-06-01", None, is_current=True)
        assert result == "Jun. 2021 -- Present"

    # -- _strip_protocol ---------------------------------------------------

    def test_strip_https(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        assert JakeResumeTemplate._strip_protocol("https://example.com") == "example.com"


# ======================================================================
# Jake template output
# ======================================================================


class TestJakeTemplate:
    """Integration-style tests that render the full template."""

    def _minimal_data(self, **overrides):
        data = {
            "contact": {"name": "Jane Doe", "email": "jane@test.com"},
            "education": [],
            "work_experience": [],
            "projects": [],
            "skills": {"tools": [], "practices": []},
        }
        data.update(overrides)
        return data

    def test_heading_present(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        doc = JakeResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert r"\begin{center}" in tex
        assert "Jane Doe" in tex

    def test_no_education_section_when_empty(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        doc = JakeResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert r"\section{Education}" not in tex

    def test_education_section(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        data = self._minimal_data(
            education=[
                {
                    "institution": "MIT",
                    "degree": "B.S.",
                    "field_of_study": "CS",
                    "start_date": "2018-08-15",
                    "end_date": "2022-05-15",
                }
            ]
        )
        doc = JakeResumeTemplate().build(data)
        tex = doc.dumps()
        assert r"\section{Education}" in tex
        assert "MIT" in tex

    def test_experience_section(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        data = self._minimal_data(
            work_experience=[
                {
                    "company": "Google",
                    "title": "SWE",
                    "bullets": ["Did things"],
                }
            ]
        )
        doc = JakeResumeTemplate().build(data)
        tex = doc.dumps()
        assert r"\section{Experience}" in tex
        assert "Google" in tex

    def test_projects_section(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        data = self._minimal_data(
            projects=[
                {
                    "name": "MyApp",
                    "technologies": ["React", "Node"],
                    "bullets": ["Built UI"],
                }
            ]
        )
        doc = JakeResumeTemplate().build(data)
        tex = doc.dumps()
        assert r"\section{Projects}" in tex
        assert "MyApp" in tex

    def test_skills_section(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        data = self._minimal_data(skills={"tools": ["Python", "Go"], "practices": ["CI/CD"]})
        doc = JakeResumeTemplate().build(data)
        tex = doc.dumps()
        assert r"\section{Technical Skills}" in tex
        assert "Python" in tex

    def test_url_not_escaped_in_href(self):
        """URLs inside \\href{} must NOT have underscores escaped."""
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        data = self._minimal_data(
            contact={
                "name": "Test",
                "linkedin_url": "https://linkedin.com/in/my_user",
            }
        )
        doc = JakeResumeTemplate().build(data)
        tex = doc.dumps()
        # Raw URL inside \href should keep underscore
        assert r"\href{https://linkedin.com/in/my_user}" in tex
        # Display text should escape it
        assert r"my\_user" in tex

    def test_education_achievements(self):
        from capstone_project_team_5.templates.jake import JakeResumeTemplate

        data = self._minimal_data(
            education=[
                {
                    "institution": "Uni",
                    "degree": "MS",
                    "achievements": ["Published paper", "TA award"],
                }
            ]
        )
        doc = JakeResumeTemplate().build(data)
        tex = doc.dumps()
        assert "Published paper" in tex
        assert "TA award" in tex


# ======================================================================
# Data builders
# ======================================================================


class TestDataBuilders:
    """Unit tests for the _build_* helpers in resume_generator."""

    def test_build_contact_full(self):
        from capstone_project_team_5.services.resume_generator import _build_contact

        profile = {
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@test.com",
            "phone": "555-1234",
            "linkedin_url": "https://linkedin.com/in/alice",
            "github_username": "asmith",
            "website": "https://alice.dev",
        }
        c = _build_contact(profile)
        assert c["name"] == "Alice Smith"
        assert c["email"] == "alice@test.com"
        assert c["github_url"] == "https://github.com/asmith"
        assert c["website_url"] == "https://alice.dev"

    def test_build_project_list(self):
        from capstone_project_team_5.services.resume_generator import (
            _build_project_list,
        )

        resumes = [
            {
                "project_name": "Proj",
                "bullet_points": ["Did X"],
                "analysis_snapshot": ["Python"],
                "project_id": 1,
            }
        ]
        dates = {1: {"start_date": date(2022, 1, 1), "end_date": date(2022, 6, 1)}}
        entries = _build_project_list(resumes, dates)
        assert entries[0]["name"] == "Proj"
        assert entries[0]["technologies"] == ["Python"]
        assert "2022-01-01" in entries[0]["start_date"]

    def test_build_skills(self):
        from capstone_project_team_5.services.resume_generator import _build_skills

        raw = [
            {"skill_name": "Python", "skill_type": SkillType.TOOL},
            {"skill_name": "TDD", "skill_type": SkillType.PRACTICE},
            {"skill_name": "Go", "skill_type": SkillType.TOOL},
        ]
        result = _build_skills(raw)
        assert result["tools"] == ["Python", "Go"]
        assert result["practices"] == ["TDD"]


# ======================================================================
# _fetch_project_dates
# ======================================================================


class TestFetchProjectDates:
    def test_returns_dates(self, tmp_db):
        from capstone_project_team_5.services.resume_generator import (
            _fetch_project_dates,
        )

        with db_module.get_session() as s:
            upload = UploadRecord(filename="a.zip", size_bytes=1, file_count=1)
            s.add(upload)
            s.flush()
            p = Project(
                upload_id=upload.id,
                name="P",
                rel_path="p",
                has_git_repo=False,
                file_count=1,
                is_collaborative=False,
                start_date=datetime(2022, 1, 1),
                end_date=datetime(2022, 12, 31),
            )
            s.add(p)
            s.commit()
            pid = p.id

        result = _fetch_project_dates([pid])
        assert pid in result
        assert result[pid]["start_date"] is not None


# ======================================================================
# aggregate_resume_data


class TestAggregateResumeData:
    def test_returns_none_without_profile(self, tmp_db):
        from capstone_project_team_5.services.resume_generator import (
            aggregate_resume_data,
        )

        with db_module.get_session() as s:
            s.add(User(username="ghost", password_hash="h"))
            s.commit()

        assert aggregate_resume_data("ghost") is None

    def test_full_aggregation(self, seeded):
        from capstone_project_team_5.services.resume_generator import (
            aggregate_resume_data,
        )

        data = aggregate_resume_data(seeded)
        assert data is not None
        assert data["contact"]["name"] == "Test User"
        assert len(data["education"]) == 1
        assert len(data["work_experience"]) == 1
        assert len(data["projects"]) == 1
        assert "Python" in data["skills"]["tools"]
        assert "TDD" in data["skills"]["practices"]


# ======================================================================
# generate_resume_tex
# ======================================================================


class TestGenerateResumeTex:
    def test_returns_tex_string(self, seeded):
        from capstone_project_team_5.services.resume_generator import (
            generate_resume_tex,
        )

        tex = generate_resume_tex(seeded)
        assert tex is not None
        assert r"\begin{document}" in tex
        assert "Test User" in tex

    def test_unknown_template_raises(self, seeded):
        from capstone_project_team_5.services.resume_generator import (
            generate_resume_tex,
        )

        with pytest.raises(ValueError, match="Unknown template"):
            generate_resume_tex(seeded, template_name="nope")


# ======================================================================
# generate_resume_pdf


class TestGenerateResumePdf:
    def test_calls_generate_pdf(self, seeded, tmp_path):
        """Mock doc.generate_pdf to verify the call chain works."""
        from capstone_project_team_5.services.resume_generator import (
            generate_resume_pdf,
        )

        with patch("capstone_project_team_5.templates.jake.JakeResumeTemplate.build") as mock_build:
            mock_doc = MagicMock()
            mock_build.return_value = mock_doc

            generate_resume_pdf(seeded, tmp_path / "out")
            mock_doc.generate_pdf.assert_called_once()

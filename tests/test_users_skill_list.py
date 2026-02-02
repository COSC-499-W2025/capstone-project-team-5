from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.constants.skill_detection_constants import SkillType
from capstone_project_team_5.data.db import Base
from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
from capstone_project_team_5.data.models.project import Project
from capstone_project_team_5.data.models.skill import ProjectSkill, Skill
from capstone_project_team_5.data.models.upload_record import UploadRecord
from capstone_project_team_5.data.models.user import User
from capstone_project_team_5.data.models.user_code_analysis import UserCodeAnalysis
from capstone_project_team_5.services.user_skill_list import (
    get_chronological_skills,
    render_skills_as_markdown,
)


@pytest.fixture(scope="function")
def tmp_db(monkeypatch, tmp_path):
    """Create a temporary test database."""

    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", TestingSessionLocal)

    yield

    engine.dispose()


@pytest.fixture
def seeded_user_with_skills(tmp_db):
    """Create a test user with multiple projects and skills."""

    with db_module.get_session() as session:
        # Create user
        user = User(username="testuser", password_hash="hash")
        session.add(user)
        session.flush()

        # Create skills
        git_skill = Skill(name="Git", skill_type=SkillType.TOOL)
        python_skill = Skill(name="Python", skill_type=SkillType.TOOL)
        testing_skill = Skill(name="Unit Testing", skill_type=SkillType.PRACTICE)
        ci_skill = Skill(name="CI/CD", skill_type=SkillType.PRACTICE)
        session.add_all([git_skill, python_skill, testing_skill, ci_skill])
        session.flush()

        # Create uploads
        upload1 = UploadRecord(filename="old_project.zip", size_bytes=1000, file_count=5)
        upload2 = UploadRecord(filename="new_project.zip", size_bytes=2000, file_count=10)
        upload3 = UploadRecord(filename="middle_project.zip", size_bytes=1500, file_count=7)
        session.add_all([upload1, upload2, upload3])
        session.flush()

        # Create projects with different timestamps
        base_time = datetime.now(UTC)

        # Oldest project (2 days ago) - Git, Python
        project1 = Project(
            upload_id=upload1.id,
            name="Old Project",
            rel_path="old_project",
            has_git_repo=True,
            file_count=5,
            is_collaborative=False,
            created_at=base_time - timedelta(days=2),
        )

        # Middle project (1 day ago) - Python, Unit Testing, CI/CD
        project2 = Project(
            upload_id=upload3.id,
            name="Middle Project",
            rel_path="middle_project",
            has_git_repo=True,
            file_count=7,
            is_collaborative=False,
            created_at=base_time - timedelta(days=1),
        )

        # Newest project (now) - Git, Unit Testing
        project3 = Project(
            upload_id=upload2.id,
            name="New Project",
            rel_path="new_project",
            has_git_repo=True,
            file_count=10,
            is_collaborative=False,
            created_at=base_time,
        )

        session.add_all([project1, project2, project3])
        session.flush()

        # Link skills to projects
        # Project 1: Git, Python
        ps1_git = ProjectSkill(project_id=project1.id, skill_id=git_skill.id)
        ps1_python = ProjectSkill(project_id=project1.id, skill_id=python_skill.id)

        # Project 2: Python, Unit Testing, CI/CD
        ps2_python = ProjectSkill(project_id=project2.id, skill_id=python_skill.id)
        ps2_testing = ProjectSkill(project_id=project2.id, skill_id=testing_skill.id)
        ps2_ci = ProjectSkill(project_id=project2.id, skill_id=ci_skill.id)

        # Project 3: Git, Unit Testing
        ps3_git = ProjectSkill(project_id=project3.id, skill_id=git_skill.id)
        ps3_testing = ProjectSkill(project_id=project3.id, skill_id=testing_skill.id)

        session.add_all(
            [ps1_git, ps1_python, ps2_python, ps2_testing, ps2_ci, ps3_git, ps3_testing]
        )
        session.flush()

        # Create CodeAnalysis entries for each project
        analysis1 = CodeAnalysis(
            project_id=project1.id,
            language="Python",
            analysis_type="local",
            metrics_json='{"lines": 100}',
            summary_text="Analysis of old project",
        )
        analysis2 = CodeAnalysis(
            project_id=project2.id,
            language="Python",
            analysis_type="local",
            metrics_json='{"lines": 200}',
            summary_text="Analysis of middle project",
        )
        analysis3 = CodeAnalysis(
            project_id=project3.id,
            language="Python",
            analysis_type="local",
            metrics_json='{"lines": 300}',
            summary_text="Analysis of new project",
        )
        session.add_all([analysis1, analysis2, analysis3])
        session.flush()

        # Link user to code analyses
        user_analysis1 = UserCodeAnalysis(user_id=user.id, analysis_id=analysis1.id)
        user_analysis2 = UserCodeAnalysis(user_id=user.id, analysis_id=analysis2.id)
        user_analysis3 = UserCodeAnalysis(user_id=user.id, analysis_id=analysis3.id)
        session.add_all([user_analysis1, user_analysis2, user_analysis3])

        session.commit()

        return user.id


@pytest.fixture
def tool_skill():
    """A single tool skill."""

    return {
        "skill_name": "Git",
        "skill_type": SkillType.TOOL,
        "first_used": datetime(2025, 3, 15, tzinfo=UTC),
    }


@pytest.fixture
def practice_skill():
    """A single practice skill."""

    return {
        "skill_name": "Unit Testing",
        "skill_type": SkillType.PRACTICE,
        "first_used": datetime(2025, 6, 1, tzinfo=UTC),
    }


@pytest.fixture
def mixed_skills():
    """Multiple tools and practices at different dates."""

    return [
        {
            "skill_name": "Git",
            "skill_type": SkillType.TOOL,
            "first_used": datetime(2025, 1, 10, tzinfo=UTC),
        },
        {
            "skill_name": "Python",
            "skill_type": SkillType.TOOL,
            "first_used": datetime(2025, 2, 5, tzinfo=UTC),
        },
        {
            "skill_name": "Unit Testing",
            "skill_type": SkillType.PRACTICE,
            "first_used": datetime(2025, 3, 1, tzinfo=UTC),
        },
        {
            "skill_name": "CI/CD",
            "skill_type": SkillType.PRACTICE,
            "first_used": datetime(2025, 4, 20, tzinfo=UTC),
        },
    ]


def test_get_chronological_skills_returns_unique_sorted_skills(seeded_user_with_skills):
    """Test that skills are unique and sorted by first usage."""

    with db_module.get_session() as session:
        skills = get_chronological_skills(session, seeded_user_with_skills)

        # Should have 4 unique skills
        assert len(skills) == 4

        # Extract skill names
        skill_names = [s["skill_name"] for s in skills]

        # Git and Python should appear first (from oldest project)
        assert skill_names[0] in ["Git", "Python"]
        assert skill_names[1] in ["Git", "Python"]

        # Unit Testing and CI/CD should appear last (from middle project)
        assert skill_names[2] in ["Unit Testing", "CI/CD"]
        assert skill_names[3] in ["Unit Testing", "CI/CD"]

        # Verify chronological ordering by checking timestamps
        for i in range(len(skills) - 1):
            assert skills[i]["first_used"] <= skills[i + 1]["first_used"]


def test_get_chronological_skills_no_duplicate_skills(seeded_user_with_skills):
    """Test that each skill appears only once even if used in multiple projects."""

    with db_module.get_session() as session:
        skills = get_chronological_skills(session, seeded_user_with_skills)

        # Check for duplicates
        skill_keys = [(s["skill_name"], s["skill_type"]) for s in skills]
        assert len(skill_keys) == len(set(skill_keys)), "Found duplicate skills"


def test_get_chronological_skills_uses_earliest_project(seeded_user_with_skills):
    """Test that skills are attributed to their earliest project usage."""

    with db_module.get_session() as session:
        skills = get_chronological_skills(session, seeded_user_with_skills)

        # Git should be from the oldest project (project1)
        git_skill = next(s for s in skills if s["skill_name"] == "Git")
        python_skill = next(s for s in skills if s["skill_name"] == "Python")

        # Git and Python should have the same (oldest) timestamp
        assert git_skill["first_used"] == python_skill["first_used"]


def test_get_chronological_skills_nonexistent_user(tmp_db):
    """Test that empty list is returned for nonexistent user."""

    with db_module.get_session() as session:
        skills = get_chronological_skills(session, 99999)

        assert skills == []


def test_get_chronological_skills_user_with_no_analyses(tmp_db):
    """Test that empty list is returned for user with no code analyses."""

    with db_module.get_session() as session:
        user = User(username="emptyuser", password_hash="hash")
        session.add(user)
        session.commit()

        skills = get_chronological_skills(session, user.id)

        assert skills == []


def test_get_chronological_skills_correct_skill_types(seeded_user_with_skills):
    """Test that skill types are correctly preserved."""

    with db_module.get_session() as session:
        skills = get_chronological_skills(session, seeded_user_with_skills)

        # Check that tools and practices are correctly typed
        git_skill = next(s for s in skills if s["skill_name"] == "Git")
        testing_skill = next(s for s in skills if s["skill_name"] == "Unit Testing")

        assert git_skill["skill_type"] == SkillType.TOOL
        assert testing_skill["skill_type"] == SkillType.PRACTICE


def test_empty_skills_returns_no_skills_message():
    """Empty list should return the no-skills placeholder."""

    result = render_skills_as_markdown([])
    assert "No skills detected" in result


def test_single_tool_renders_tools_section(tool_skill):
    """A single tool should appear under the Tools heading with correct date."""

    result = render_skills_as_markdown([tool_skill])
    assert "## Tools" in result
    assert "**Git**" in result
    assert "Mar 2025" in result


def test_single_tool_does_not_render_practices_section(tool_skill):
    """If there are no practices, the Practices heading should not appear."""

    result = render_skills_as_markdown([tool_skill])
    assert "## Practices" not in result


def test_single_practice_renders_practices_section(practice_skill):
    """A single practice should appear under the Practices heading."""

    result = render_skills_as_markdown([practice_skill])
    assert "## Practices" in result
    assert "**Unit Testing**" in result
    assert "Jun 2025" in result


def test_single_practice_does_not_render_tools_section(practice_skill):
    """If there are no tools, the Tools heading should not appear."""

    result = render_skills_as_markdown([practice_skill])
    assert "## Tools" not in result


def test_mixed_skills_renders_both_sections(mixed_skills):
    """Both Tools and Practices sections should appear when both types exist."""

    result = render_skills_as_markdown(mixed_skills)
    assert "## Tools" in result
    assert "## Practices" in result
    assert "**Git**" in result
    assert "**Python**" in result
    assert "**Unit Testing**" in result
    assert "**CI/CD**" in result


def test_summary_line_plural_tools_and_practices(mixed_skills):
    """Summary should use plural forms when there are multiple of each type."""

    result = render_skills_as_markdown(mixed_skills)
    assert "2 tools" in result
    assert "2 practices" in result


def test_summary_line_singular_tool_and_practice(tool_skill, practice_skill):
    """Summary should use singular forms when there is one of each type."""

    result = render_skills_as_markdown([tool_skill, practice_skill])
    assert "1 tool," in result
    assert "1 practice" in result


def test_tools_only_summary_singular_practice(mixed_skills):
    """Summary should use singular 'practice' when count is 0."""

    tools_only = [s for s in mixed_skills if s["skill_type"] == SkillType.TOOL]
    result = render_skills_as_markdown(tools_only)
    assert "2 tools" in result
    assert "0 practice" in result
    assert "0 practices" not in result


def test_practices_only_summary_singular_tool(mixed_skills):
    """Summary should use singular 'tool' when count is 0."""

    practices_only = [s for s in mixed_skills if s["skill_type"] == SkillType.PRACTICE]
    result = render_skills_as_markdown(practices_only)
    assert "0 tool," in result
    assert "0 tools" not in result
    assert "2 practices" in result

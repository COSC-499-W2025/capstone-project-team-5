"""Tests for resume templates (Rover, Modern) and shared helpers."""


# ======================================================================
# Base class helper — _strip_protocol
# ======================================================================


class TestBaseStripProtocol:
    def test_strip_https(self):
        from capstone_project_team_5.templates.base import ResumeTemplate

        assert ResumeTemplate._strip_protocol("https://example.com") == "example.com"

    def test_strip_http(self):
        from capstone_project_team_5.templates.base import ResumeTemplate

        assert ResumeTemplate._strip_protocol("http://example.com") == "example.com"

    def test_no_protocol(self):
        from capstone_project_team_5.templates.base import ResumeTemplate

        assert ResumeTemplate._strip_protocol("example.com") == "example.com"


# ======================================================================
# Rover Template
# ======================================================================


class TestRoverTemplate:
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
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

        doc = RoverResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert "Jane Doe" in tex

    def test_no_education_when_empty(self):
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

        doc = RoverResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert r"\section{Education}" not in tex

    def test_education_section(self):
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

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
        tex = RoverResumeTemplate().build(data).dumps()
        assert "MIT" in tex

    def test_experience_section(self):
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

        data = self._minimal_data(
            work_experience=[
                {
                    "company": "Google",
                    "title": "SWE",
                    "bullets": ["Did things"],
                }
            ]
        )
        tex = RoverResumeTemplate().build(data).dumps()
        assert "Google" in tex

    def test_projects_section(self):
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

        data = self._minimal_data(
            projects=[
                {
                    "name": "MyApp",
                    "technologies": ["React", "Node"],
                    "bullets": ["Built UI"],
                }
            ]
        )
        tex = RoverResumeTemplate().build(data).dumps()
        assert "MyApp" in tex

    def test_skills_section(self):
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

        data = self._minimal_data(skills={"tools": ["Python", "Go"], "practices": ["CI/CD"]})
        tex = RoverResumeTemplate().build(data).dumps()
        assert "Python" in tex

    def test_url_not_escaped_in_href(self):
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

        data = self._minimal_data(
            contact={
                "name": "Test",
                "linkedin_url": "https://linkedin.com/in/my_user",
            }
        )
        tex = RoverResumeTemplate().build(data).dumps()
        assert r"\href{https://linkedin.com/in/my_user}" in tex
        assert r"my\_user" in tex

    def test_education_achievements(self):
        from capstone_project_team_5.templates.rover import RoverResumeTemplate

        data = self._minimal_data(
            education=[
                {
                    "institution": "Uni",
                    "degree": "MS",
                    "achievements": ["Published paper", "TA award"],
                }
            ]
        )
        tex = RoverResumeTemplate().build(data).dumps()
        assert "Published paper" in tex
        assert "TA award" in tex

    def test_get_rover(self):
        from capstone_project_team_5.templates import get_template

        t = get_template("rover")
        assert t.name == "Rover Resume"


# ======================================================================
# Modern Template
# ======================================================================


class TestModernTemplate:
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
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        doc = ModernResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert "Jane Doe" in tex

    def test_sans_serif_preamble(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        doc = ModernResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert r"\sfdefault" in tex

    def test_no_titlerule(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        doc = ModernResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert r"\titlerule" not in tex

    def test_no_education_when_empty(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        doc = ModernResumeTemplate().build(self._minimal_data())
        tex = doc.dumps()
        assert r"\section{Education}" not in tex

    def test_education_section(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

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
        tex = ModernResumeTemplate().build(data).dumps()
        assert "MIT" in tex

    def test_experience_section(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        data = self._minimal_data(
            work_experience=[
                {
                    "company": "Google",
                    "title": "SWE",
                    "bullets": ["Did things"],
                }
            ]
        )
        tex = ModernResumeTemplate().build(data).dumps()
        assert "Google" in tex

    def test_projects_section(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        data = self._minimal_data(
            projects=[
                {
                    "name": "MyApp",
                    "technologies": ["React", "Node"],
                    "bullets": ["Built UI"],
                }
            ]
        )
        tex = ModernResumeTemplate().build(data).dumps()
        assert "MyApp" in tex

    def test_skills_section(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        data = self._minimal_data(skills={"tools": ["Python", "Go"], "practices": ["CI/CD"]})
        tex = ModernResumeTemplate().build(data).dumps()
        assert "Python" in tex

    def test_url_not_escaped_in_href(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        data = self._minimal_data(
            contact={
                "name": "Test",
                "linkedin_url": "https://linkedin.com/in/my_user",
            }
        )
        tex = ModernResumeTemplate().build(data).dumps()
        assert r"\href{https://linkedin.com/in/my_user}" in tex
        assert r"my\_user" in tex

    def test_education_achievements(self):
        from capstone_project_team_5.templates.modern import ModernResumeTemplate

        data = self._minimal_data(
            education=[
                {
                    "institution": "Uni",
                    "degree": "MS",
                    "achievements": ["Published paper", "TA award"],
                }
            ]
        )
        tex = ModernResumeTemplate().build(data).dumps()
        assert "Published paper" in tex
        assert "TA award" in tex

    def test_get_modern(self):
        from capstone_project_team_5.templates import get_template

        t = get_template("modern")
        assert t.name == "Modern Resume"


# ======================================================================
# Integration — all templates registered
# ======================================================================


class TestTemplateRegistry:
    def test_list_templates_includes_all(self):
        from capstone_project_team_5.templates import list_templates

        names = list_templates()
        assert set(names) == {"jake", "rover", "modern"}

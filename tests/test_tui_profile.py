"""Test suite for TUI personal profile integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import capstone_project_team_5.data.db as db_module
from capstone_project_team_5.data.models import Base, User
from capstone_project_team_5.tui import Zip2JobTUI


@pytest.fixture(scope="function")
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    """Create a temporary test database."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db_module, "_engine", engine)
    monkeypatch.setattr(db_module, "_SessionLocal", sessionmaker(bind=engine))
    yield
    engine.dispose()


@pytest.fixture()
def test_user(tmp_db: None) -> str:
    """Create a test user and return username."""
    with db_module.get_session() as s:
        u = User(username="profileuser", password_hash="hash")
        s.add(u)
        s.commit()
    return "profileuser"


class TestRenderProfileMarkdown:
    """Tests for Zip2JobTUI._render_profile_markdown helper."""

    def test_render_no_profile(self) -> None:
        """When profile is None, the markdown should indicate no data."""
        app = Zip2JobTUI()
        md = app._render_profile_markdown(None)
        assert "# My Profile" in md
        assert "No profile information saved yet" in md
        assert "Edit Personal Info" in md

    def test_render_with_profile_data_and_empty_fields(self) -> None:
        """Populated fields appear; missing/empty fields render as em-dash."""
        app = Zip2JobTUI()
        full = {
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice@example.com",
            "phone": "555-0000",
            "address": "1 Main St",
            "city": "Metropolis",
            "state": "NY",
            "zip_code": "10001",
            "linkedin_url": "https://linkedin.com/in/alice",
            "github_username": "alicedev",
            "website": "https://alice.dev",
            "updated_at": "2025-01-15 10:30:00",
        }
        md = app._render_profile_markdown(full)
        for val in ("Alice", "Smith", "alice@example.com", "alicedev", "Last updated"):
            assert val in md

        sparse = {"first_name": "Bob", "last_name": "", "email": None}
        md2 = app._render_profile_markdown(sparse)
        assert "Bob" in md2
        assert "\u2014" in md2


class TestPromptEditProfile:
    """Tests for the _prompt_edit_profile dialog flow."""

    def test_cancelled_dialog_does_not_save(self, test_user: str) -> None:
        """If the user cancels the easygui dialog, no profile upsert happens."""
        app = Zip2JobTUI()
        app._current_user = test_user

        # Stub out TUI widget queries
        mock_status = MagicMock()
        mock_output = MagicMock()
        app.query_one = MagicMock(
            side_effect=lambda sel, cls=None: mock_status if "status" in sel else mock_output
        )  # noqa: E501

        with patch("easygui.multenterbox", return_value=None):
            app._prompt_edit_profile()

        mock_status.update.assert_called_with("Profile edit cancelled.")

    def test_successful_edit_calls_upsert(self, test_user: str) -> None:
        """A completed dialog should call upsert and refresh the output."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        mock_output = MagicMock()

        def _query_one(sel: str, cls: type | None = None) -> MagicMock:
            if "status" in sel:
                return mock_status
            return mock_output

        app.query_one = MagicMock(side_effect=_query_one)  # type: ignore[assignment]

        dialog_values = [
            "Alice",  # first_name
            "Smith",  # last_name
            "a@b.com",  # email
            "555-1111",  # phone
            "1 Oak St",  # address
            "Gotham",  # city
            "NJ",  # state
            "07001",  # zip_code
            "https://li",  # linkedin_url
            "asmith",  # github_username
            "https://a.io",  # website
        ]

        with (
            patch("easygui.multenterbox", return_value=dialog_values),
            patch(
                "capstone_project_team_5.tui.upsert_user_profile",
                return_value={
                    "first_name": "Alice",
                    "last_name": "Smith",
                    "email": "a@b.com",
                },
            ) as mock_upsert,
        ):
            app._prompt_edit_profile()

        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args
        assert call_args[0][0] == test_user
        assert call_args[0][1]["first_name"] == "Alice"
        mock_status.update.assert_called_with("Profile updated successfully.")

    def test_upsert_failure_shows_error(self, test_user: str) -> None:
        """When upsert returns None the status should report failure."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        mock_output = MagicMock()
        app.query_one = MagicMock(
            side_effect=lambda sel, cls=None: mock_status if "status" in sel else mock_output
        )  # noqa: E501

        dialog_values = [""] * 11  # all blank

        with (
            patch("easygui.multenterbox", return_value=dialog_values),
            patch(
                "capstone_project_team_5.tui.upsert_user_profile",
                return_value=None,
            ),
        ):
            app._prompt_edit_profile()

        mock_status.update.assert_called_with("Failed to save profile. Please try again.")

    def test_not_logged_in_shows_error(self) -> None:
        """Editing profile without logging in should show an error."""
        app = Zip2JobTUI()
        app._current_user = None

        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_status)

        app._prompt_edit_profile()
        mock_status.update.assert_called_with("Please log in before editing your profile.")


class TestProfileViewToggle:
    """Tests for profile sub-button visibility and list-column toggling."""

    @staticmethod
    def _make_mock_widgets() -> dict[str, MagicMock]:
        """Create a dict of mock widgets keyed by selector."""
        return {
            "#btn-edit-personal-info": MagicMock(),
            "#btn-edit-work-exp": MagicMock(),
            "#btn-edit-education": MagicMock(),
            "#list-column": MagicMock(),
            "#status": MagicMock(),
            "#output": MagicMock(),
            "#btn-delete-analysis": MagicMock(),
            "#btn-export-pdf": MagicMock(),
            "#btn-export-txt": MagicMock(),
        }

    @staticmethod
    def _wire_query_one(app: Zip2JobTUI, widgets: dict[str, MagicMock]) -> None:
        """Replace query_one with a lookup into the mock widgets dict."""

        def _query_one(sel: str, cls: type | None = None) -> MagicMock:
            for key, mock in widgets.items():
                if key in sel:
                    return mock
            return MagicMock()

        app.query_one = MagicMock(side_effect=_query_one)  # type: ignore[assignment]

    def test_leave_profile_view_hides_buttons_and_restores_list(self) -> None:
        """_leave_profile_view should hide sub-buttons and restore #list-column."""
        app = Zip2JobTUI()
        widgets = self._make_mock_widgets()
        self._wire_query_one(app, widgets)

        app._leave_profile_view()

        assert widgets["#btn-edit-personal-info"].display is False
        assert widgets["#btn-edit-work-exp"].display is False
        assert widgets["#btn-edit-education"].display is False
        assert widgets["#list-column"].display is True

    def test_handle_profile_shows_sub_buttons_and_hides_list(self, test_user: str) -> None:
        """handle_profile_button should show sub-buttons and hide list-column."""
        app = Zip2JobTUI()
        app._current_user = test_user
        widgets = self._make_mock_widgets()
        self._wire_query_one(app, widgets)

        with (
            patch("capstone_project_team_5.tui.get_user_profile", return_value=None),
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
        ):
            app.handle_profile_button()

        # Sub-buttons shown
        assert widgets["#btn-edit-personal-info"].display is True
        assert widgets["#btn-edit-work-exp"].display is True
        assert widgets["#btn-edit-education"].display is True
        # List column hidden
        assert widgets["#list-column"].display is False
        # Status updated
        widgets["#status"].update.assert_called_with("Viewing personal profile.")


class TestRenderEducationMarkdown:
    """Tests for education rendering within _render_profile_markdown."""

    def test_no_educations_shows_placeholder(self) -> None:
        """When educations list is empty, show placeholder text."""
        app = Zip2JobTUI()
        md = app._render_profile_markdown(None, educations=[])
        assert "## Education" in md
        assert "No education entries yet" in md
        assert "Edit Education" in md

    def test_education_entries_rendered(self) -> None:
        """Education entries render fields, is_current, and multiple entries."""
        app = Zip2JobTUI()
        educations = [
            {
                "institution": "MIT",
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "gpa": 3.9,
                "start_date": "2018-09-01",
                "end_date": "2022-05-15",
                "is_current": False,
                "achievements": "Dean's List",
            },
            {
                "institution": "Stanford",
                "degree": "Ph.D.",
                "field_of_study": "AI",
                "start_date": "2023-09-01",
                "end_date": None,
                "is_current": True,
                "gpa": None,
                "achievements": "",
            },
        ]
        md = app._render_profile_markdown(None, educations=educations)
        # First entry fields
        for val in ("### MIT", "**B.S.**", "Computer Science", "3.9", "Dean's List"):
            assert val in md
        # Second entry + is_current
        assert "Stanford" in md
        assert "Present" in md
        # Placeholder should NOT appear
        assert "No education entries yet" not in md


class TestPromptEditEducation:
    """Tests for the _prompt_edit_education dialog flow."""

    def test_cancellation_at_any_step_does_not_save(self, test_user: str) -> None:
        """Cancelling the choice dialog or the form dialog should not save."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_status)

        # Cancel at choicebox
        with (
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
            patch("easygui.choicebox", return_value=None),
        ):
            app._prompt_edit_education()
        mock_status.update.assert_called_with("Education edit cancelled.")

        # Cancel at form
        mock_status.reset_mock()
        with (
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
            patch("easygui.choicebox", return_value="+ Add New Education"),
            patch("easygui.multenterbox", return_value=None),
        ):
            app._prompt_edit_education()
        mock_status.update.assert_called_with("Education edit cancelled.")

    def test_add_new_education_success(self, test_user: str) -> None:
        """Selecting 'Add New Education' and filling the form should create an entry."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        mock_output = MagicMock()
        app.query_one = MagicMock(
            side_effect=lambda sel, cls=None: mock_status if "status" in sel else mock_output
        )

        form_values = [
            "MIT",  # Institution
            "B.S.",  # Degree
            "CS",  # Field of Study
            "3.8",  # GPA
            "2020-09-01",  # Start Date
            "2024-05-15",  # End Date
            "no",  # Currently Enrolled
            "Honors",  # Achievements
        ]

        with (
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
            patch("easygui.choicebox", return_value="+ Add New Education"),
            patch("easygui.multenterbox", return_value=form_values),
            patch(
                "capstone_project_team_5.tui.create_education",
                return_value={"institution": "MIT", "degree": "B.S."},
            ) as mock_create,
            patch("capstone_project_team_5.tui.get_user_profile", return_value=None),
        ):
            app._prompt_edit_education()

        mock_create.assert_called_once()
        call_data = mock_create.call_args[0][1]
        assert call_data["institution"] == "MIT"
        assert call_data["degree"] == "B.S."
        mock_status.update.assert_called_with("Education saved successfully.")

    def test_edit_existing_education_success(self, test_user: str) -> None:
        """Selecting an existing entry and updating it should call update_education."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        mock_output = MagicMock()
        app.query_one = MagicMock(
            side_effect=lambda sel, cls=None: mock_status if "status" in sel else mock_output
        )

        existing_educations = [
            {
                "id": 42,
                "institution": "Harvard",
                "degree": "MBA",
                "field_of_study": "Business",
                "gpa": 3.5,
                "start_date": "2019-09-01",
                "end_date": "2021-05-15",
                "is_current": False,
                "achievements": "",
            },
        ]

        form_values = [
            "Harvard",
            "MBA",
            "Finance",  # changed field
            "3.7",  # changed GPA
            "2019-09-01",
            "2021-05-15",
            "no",
            "Magna Cum Laude",
        ]

        with (
            patch(
                "capstone_project_team_5.tui.get_educations",
                return_value=existing_educations,
            ),
            patch("easygui.choicebox", return_value="Harvard – MBA"),
            patch("easygui.buttonbox", return_value="Edit"),
            patch("easygui.multenterbox", return_value=form_values),
            patch(
                "capstone_project_team_5.tui.update_education",
                return_value={"institution": "Harvard", "degree": "MBA"},
            ) as mock_update,
            patch("capstone_project_team_5.tui.get_user_profile", return_value=None),
        ):
            app._prompt_edit_education()

        mock_update.assert_called_once()
        assert mock_update.call_args[0][0] == test_user
        assert mock_update.call_args[0][1] == 42
        call_data = mock_update.call_args[0][2]
        assert call_data["field_of_study"] == "Finance"
        mock_status.update.assert_called_with("Education saved successfully.")

    def test_missing_required_fields_shows_error(self, test_user: str) -> None:
        """If institution or degree is blank, validation should fail."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_status)

        form_values = ["", "", "", "", "", "", "no", ""]  # all blank

        with (
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
            patch("easygui.choicebox", return_value="+ Add New Education"),
            patch("easygui.multenterbox", return_value=form_values),
            patch("easygui.msgbox") as mock_msgbox,
        ):
            app._prompt_edit_education()

        mock_msgbox.assert_called_once()
        assert "required" in mock_msgbox.call_args[0][0].lower()
        mock_status.update.assert_called_with("Education save failed: missing required fields.")

    def test_invalid_input_shows_validation_errors(self, test_user: str) -> None:
        """Non-numeric GPA and malformed dates should show validation errors."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_status)

        # Bad GPA
        with (
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
            patch("easygui.choicebox", return_value="+ Add New Education"),
            patch(
                "easygui.multenterbox", return_value=["MIT", "B.S.", "CS", "abc", "", "", "no", ""]
            ),
            patch("easygui.msgbox") as mock_msgbox,
        ):
            app._prompt_edit_education()
        assert "GPA" in mock_msgbox.call_args[0][0]
        mock_status.update.assert_called_with("Education save failed: invalid GPA.")

        # Bad start date
        mock_status.reset_mock()
        with (
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
            patch("easygui.choicebox", return_value="+ Add New Education"),
            patch(
                "easygui.multenterbox",
                return_value=["MIT", "B.S.", "", "", "not-a-date", "", "no", ""],
            ),
            patch("easygui.msgbox"),
        ):
            app._prompt_edit_education()
        mock_status.update.assert_called_with("Education save failed: invalid start date.")

    def test_save_failure_shows_error(self, test_user: str) -> None:
        """When create_education returns None, status should report failure."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_status)

        form_values = ["MIT", "B.S.", "", "", "", "", "no", ""]

        with (
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
            patch("easygui.choicebox", return_value="+ Add New Education"),
            patch("easygui.multenterbox", return_value=form_values),
            patch("capstone_project_team_5.tui.create_education", return_value=None),
        ):
            app._prompt_edit_education()

        mock_status.update.assert_called_with(
            "Failed to save education. Check your input and try again."
        )


class TestDeleteEducation:
    """Tests for education deletion flow."""

    def test_delete_confirmed_success(self, test_user: str) -> None:
        """Confirming delete should call delete_education and refresh view."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        mock_output = MagicMock()
        app.query_one = MagicMock(
            side_effect=lambda sel, cls=None: mock_status if "status" in sel else mock_output
        )

        edu = {"id": 7, "institution": "MIT", "degree": "B.S."}

        with (
            patch("easygui.ynbox", return_value=True),
            patch("capstone_project_team_5.tui.delete_education", return_value=True) as mock_del,
            patch("capstone_project_team_5.tui.get_user_profile", return_value=None),
            patch("capstone_project_team_5.tui.get_educations", return_value=[]),
        ):
            app._delete_education_entry(7, edu)

        mock_del.assert_called_once_with(test_user, 7)
        mock_status.update.assert_called_with("Education entry deleted.")

    def test_delete_cancelled(self, test_user: str) -> None:
        """Declining the confirmation should not delete."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_status)

        edu = {"id": 7, "institution": "MIT", "degree": "B.S."}

        with patch("easygui.ynbox", return_value=False):
            app._delete_education_entry(7, edu)

        mock_status.update.assert_called_with("Education deletion cancelled.")

    def test_delete_failure_shows_error(self, test_user: str) -> None:
        """When delete_education returns False, status should report failure."""
        app = Zip2JobTUI()
        app._current_user = test_user

        mock_status = MagicMock()
        app.query_one = MagicMock(return_value=mock_status)

        edu = {"id": 7, "institution": "MIT", "degree": "B.S."}

        with (
            patch("easygui.ynbox", return_value=True),
            patch("capstone_project_team_5.tui.delete_education", return_value=False),
        ):
            app._delete_education_entry(7, edu)

        mock_status.update.assert_called_with("Failed to delete education entry.")

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

    def test_render_with_profile_data(self) -> None:
        """Fields present in the profile dict should appear in the markdown."""
        app = Zip2JobTUI()
        profile = {
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
        md = app._render_profile_markdown(profile)
        assert "Alice" in md
        assert "Smith" in md
        assert "alice@example.com" in md
        assert "555-0000" in md
        assert "Metropolis" in md
        assert "NY" in md
        assert "10001" in md
        assert "alicedev" in md
        assert "https://alice.dev" in md
        assert "Last updated" in md

    def test_render_with_empty_fields_shows_dash(self) -> None:
        """Missing or empty fields should display as em-dash."""
        app = Zip2JobTUI()
        profile = {
            "first_name": "Bob",
            "last_name": "",
            "email": None,
            "phone": None,
            "address": None,
            "city": None,
            "state": None,
            "zip_code": None,
            "linkedin_url": None,
            "github_username": None,
            "website": None,
        }
        md = app._render_profile_markdown(profile)
        assert "Bob" in md
        # Empty / None fields should render as the em-dash placeholder
        assert "\u2014" in md


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

    def test_leave_profile_view_hides_sub_buttons(self) -> None:
        """_leave_profile_view should hide all three sub-buttons."""
        app = Zip2JobTUI()
        widgets = self._make_mock_widgets()
        self._wire_query_one(app, widgets)

        app._leave_profile_view()

        assert widgets["#btn-edit-personal-info"].display is False
        assert widgets["#btn-edit-work-exp"].display is False
        assert widgets["#btn-edit-education"].display is False

    def test_leave_profile_view_restores_list_column(self) -> None:
        """_leave_profile_view should make #list-column visible again."""
        app = Zip2JobTUI()
        widgets = self._make_mock_widgets()
        self._wire_query_one(app, widgets)

        app._leave_profile_view()

        assert widgets["#list-column"].display is True

    def test_handle_profile_shows_sub_buttons_and_hides_list(self, test_user: str) -> None:
        """handle_profile_button should show sub-buttons and hide list-column."""
        app = Zip2JobTUI()
        app._current_user = test_user
        widgets = self._make_mock_widgets()
        self._wire_query_one(app, widgets)

        with patch("capstone_project_team_5.tui.get_user_profile", return_value=None):
            app.handle_profile_button()

        # Sub-buttons shown
        assert widgets["#btn-edit-personal-info"].display is True
        assert widgets["#btn-edit-work-exp"].display is True
        assert widgets["#btn-edit-education"].display is True
        # List column hidden
        assert widgets["#list-column"].display is False
        # Status updated
        widgets["#status"].update.assert_called_with("Viewing personal profile.")

    def test_handle_profile_not_logged_in(self) -> None:
        """handle_profile_button should show error when not logged in."""
        app = Zip2JobTUI()
        app._current_user = None
        widgets = self._make_mock_widgets()
        self._wire_query_one(app, widgets)

        app.handle_profile_button()

        widgets["#status"].update.assert_called_with("Please log in before viewing your profile.")
        # Sub-buttons should NOT have been set to True
        assert widgets["#btn-edit-personal-info"].display != True  # noqa: E712

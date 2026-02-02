from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    ProgressBar,
    Static,
    TextArea,
)
from textual.worker import Worker, WorkerState

from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.services import create_portfolio_item, upload_zip
from capstone_project_team_5.services.auth import authenticate_user, create_user
from capstone_project_team_5.services.portfolio_persistence import (
    get_latest_portfolio_item_for_project,
)
from capstone_project_team_5.services.project_thumbnail import (
    THUMBNAIL_EXTENSIONS,
    clear_project_thumbnail,
    has_project_thumbnail,
    set_project_thumbnail,
)
from capstone_project_team_5.services.user_skill_list import (
    get_chronological_skills,
    render_skills_as_markdown,
)
from capstone_project_team_5.tui_rendering import (
    render_detected_list,
    render_project_markdown,
)
from capstone_project_team_5.utils import prompt_for_zip_file
from capstone_project_team_5.workflows.analysis_pipeline import analyze_projects_structured

if TYPE_CHECKING:
    from capstone_project_team_5.data.models.code_analysis import CodeAnalysis
    from capstone_project_team_5.data.models.project import Project


ViewMode = Literal["analysis", "saved"]


class Zip2JobTUI(App[None]):
    """Modern, scrollable TUI for Zip2Job."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("e", "toggle_edit", "Edit view"),
        ("ctrl+s", "save_edit", "Save edit"),
        ("escape", "cancel_edit", "Cancel edit"),
        ("p", "export_pdf", "Export PDF"),
        ("t", "export_txt", "Export TXT"),
    ]

    CSS = """
Screen {
    layout: vertical;
    background: $background;
}

/* Auth screen centered content */
#auth-screen {
    height: 1fr;
    layout: vertical;
    align-horizontal: center;
    align-vertical: middle;
}

#auth-card {
    padding: 2;
    border: heavy $primary;
    background: $panel;
    width: 40;
    align-horizontal: center;
}

#auth-card Static {
    text-align: center;
    margin-bottom: 1;
}

#auth-card Button,
#auth-card Input {
    width: 100%;
    margin-top: 1;
}

/* Middle split: sidebar + main output */
#middle {
    height: 1fr;
    layout: horizontal;
}

/* Sidebar */
#sidebar {
    width: 26;
    padding: 2;
    border: heavy $primary;
    background: $panel;
}

#sidebar Button {
    margin-top: 1;
    width: 100%;
}

#btn-delete-analysis {
    margin-left: 2;
    width: 18;
}

#title {
    text-align: center;
    margin-bottom: 2;
    color: $text;
}

/* Main scroll area */
#main {
    border: heavy $primary;
    background: $surface;
    height: 1fr;
    padding: 1;
    layout: horizontal;
}

#output-container {
    height: 1fr;
}

#output {
    color: $text;
    padding: 1;
}

/* Status bar */
#statusbar {
    height: auto;
    padding: 1;
    border: heavy $primary;
    background: $panel;
    color: $text;
}

/* ProgressBar styling */
ProgressBar {
    dock: bottom;
    margin-top: 1;
}
"""

    def __init__(self) -> None:
        super().__init__()
        self._consent_tool: ConsentTool | None = None
        self._worker: Worker[dict] | None = None
        self._current_markdown: str = ""
        self._view_mode: ViewMode = "analysis"
        self._current_user: str | None = None
        self._auth_mode: str | None = None
        self._upload_summary: dict | None = None
        self._projects: list[dict] = []
        self._ranks: dict[int, int] = {}
        self._saved_uploads: list[dict] = []
        self._saved_projects: list[dict] = []
        self._saved_active_project_index: int | None = None
        self._analysis_selected: bool = False

    def compose(self) -> ComposeResult:
        yield Header()

        yield Container(
            # Auth screen (shown first)
            Container(
                Container(
                    Static("Zip2Job Analyzer", id="auth-title"),
                    Button("Login", id="auth-btn-login", variant="primary"),
                    Button("Sign Up", id="auth-btn-signup", variant="default"),
                    Input(placeholder="Username", id="auth-username"),
                    Input(
                        placeholder="Password",
                        password=True,
                        id="auth-password",
                    ),
                    Button("Submit", id="auth-btn-submit", variant="success"),
                    id="auth-card",
                ),
                id="auth-screen",
            ),
            # Main app screen (hidden until login)
            Container(
                # Middle region: sidebar + main scroll area
                Container(
                    # Sidebar
                    Container(
                        Static("Zip2Job\nAnalyzer", id="title"),
                        Label("Hi, -", id="user-label"),
                        Button("Log Out", id="btn-logout", variant="default"),
                        Button("Analyze ZIP", id="btn-analyze", variant="primary"),
                        Button("Retrieve Projects", id="btn-retrieve", variant="default"),
                        Button("View Skills", id="btn-skills", variant="default"),
                        Button("Delete Analysis", id="btn-delete-analysis", variant="error"),
                        Button("Set Thumbnail", id="btn-set-thumbnail", variant="default"),
                        Button("Configure Consent", id="btn-config", variant="default"),
                        Button("Edit View", id="btn-edit", variant="default"),
                        Button("Export PDF", id="btn-export-pdf", variant="default"),
                        Button("Export TXT", id="btn-export-txt", variant="default"),
                        Button("Exit", id="btn-exit", variant="error"),
                        id="sidebar",
                    ),
                    # Main area
                    Container(
                        Container(
                            # Left: project + analysis lists
                            Container(
                                ListView(id="project-list"),
                                ListView(id="analysis-list"),
                                id="list-column",
                            ),
                            # Right: detail markdown/editor
                            VerticalScroll(
                                Markdown("", id="output"),
                                TextArea(
                                    "",
                                    id="editor",
                                    # Use plain text to avoid missing language errors.
                                    language=None,
                                    placeholder="Edit analysis markdown...",
                                ),
                                id="output-container",
                            ),
                            id="main",
                        ),
                    ),
                    id="middle",
                ),
                # Status bar
                Container(
                    Label("Ready.", id="status"),
                    ProgressBar(total=100, id="progress"),
                    id="statusbar",
                ),
                id="app-screen",
            ),
        )

        yield Footer()

    def on_mount(self) -> None:
        editor = self.query_one("#editor", TextArea)
        analysis_list = self.query_one("#analysis-list", ListView)
        username_input = self.query_one("#auth-username", Input)
        password_input = self.query_one("#auth-password", Input)
        submit_btn = self.query_one("#auth-btn-submit", Button)
        app_screen = self.query_one("#app-screen", Container)
        delete_btn = self.query_one("#btn-delete-analysis", Button)
        set_thumb_btn = self.query_one("#btn-set-thumbnail", Button)
        export_pdf_btn = self.query_one("#btn-export-pdf", Button)
        export_txt_btn = self.query_one("#btn-export-txt", Button)

        editor.display = False
        analysis_list.display = False
        delete_btn.display = False
        export_pdf_btn.display = False
        export_txt_btn.display = False
        # Auth inputs are hidden until user chooses login or signup.
        username_input.display = False
        password_input.display = False
        submit_btn.display = False
        # Hide main app screen until a user logs in.
        app_screen.display = False
        set_thumb_btn.display = False

    def _reset_analysis_selection_ui(self) -> None:
        """Clear analysis selection state and hide the delete/export buttons."""
        self._analysis_selected = False
        delete_btn = self.query_one("#btn-delete-analysis", Button)
        delete_btn.display = False
        export_pdf_btn = self.query_one("#btn-export-pdf", Button)
        export_txt_btn = self.query_one("#btn-export-txt", Button)
        export_pdf_btn.display = False
        export_txt_btn.display = False

    def _current_saved_project_id(self) -> int | None:
        """Return the currently selected saved project ID, if any."""
        if self._saved_active_project_index is None:
            return None
        if not self._saved_projects:
            return None
        if self._saved_active_project_index < 0 or self._saved_active_project_index >= len(
            self._saved_projects
        ):
            return None
        proj_id = self._saved_projects[self._saved_active_project_index].get("id")
        return int(proj_id) if isinstance(proj_id, int) else None

    def _update_thumbnail_buttons(self, project_id: int | None) -> None:
        """Enable/disable thumbnail actions based on current state."""
        set_btn = self.query_one("#btn-set-thumbnail", Button)
        enabled = (
            self._view_mode == "saved" and self._current_user is not None and project_id is not None
        )
        set_btn.display = enabled
        if enabled:
            self._set_thumbnail_button_label(project_id)
        else:
            set_btn.label = "Set Thumbnail"

    def _set_thumbnail_button_label(self, project_id: int | None) -> None:
        """Toggle the button label based on whether a thumbnail is set."""
        set_btn = self.query_one("#btn-set-thumbnail", Button)
        if project_id is None:
            set_btn.label = "Set Thumbnail"
            return
        set_btn.label = "Clear Thumbnail" if has_project_thumbnail(project_id) else "Set Thumbnail"

    def _thumbnail_status_line(self, project_id: int | None) -> str:
        """Return a single-line status about the current thumbnail."""
        if project_id is None:
            return "- Thumbnail: none"
        return "- Thumbnail: set" if has_project_thumbnail(project_id) else "- Thumbnail: none set"

    def _prompt_for_thumbnail_file(self) -> Path | None:
        """Prompt the user to select a thumbnail image file."""
        import easygui

        patterns = [f"*{ext}" for ext in THUMBNAIL_EXTENSIONS]
        selected = easygui.fileopenbox(
            msg="Select a thumbnail image",
            title="Select Thumbnail",
            filetypes=patterns,
        )
        if not selected:
            return None
        return Path(selected)

    def _show_editor(self) -> None:
        """Show the markdown editor and hide the rendered output."""
        output = self.query_one("#output", Markdown)
        editor = self.query_one("#editor", TextArea)
        editor.display = True
        output.display = False
        editor.focus()

    def _hide_editor(self) -> None:
        """Hide the markdown editor and show the rendered output."""
        output = self.query_one("#output", Markdown)
        editor = self.query_one("#editor", TextArea)
        editor.display = False
        output.display = True

    # ---------------------------------------------------------------------
    # EVENTS
    # ---------------------------------------------------------------------

    # ---- Auth buttons ---------------------------------------------------

    @on(Button.Pressed, "#auth-btn-login")
    def handle_login_button(self) -> None:
        """Start the login flow by showing auth inputs."""
        self._auth_mode = "login"
        status = self.query_one("#status", Label)
        username_input = self.query_one("#auth-username", Input)
        password_input = self.query_one("#auth-password", Input)
        submit_btn = self.query_one("#auth-btn-submit", Button)

        username_input.value = ""
        password_input.value = ""
        username_input.display = True
        password_input.display = True
        submit_btn.display = True
        username_input.focus()
        status.update("Login: enter username and password, then Submit.")

    @on(Button.Pressed, "#auth-btn-signup")
    def handle_signup_button(self) -> None:
        """Start the signup flow by showing auth inputs."""
        self._auth_mode = "signup"
        status = self.query_one("#status", Label)
        username_input = self.query_one("#auth-username", Input)
        password_input = self.query_one("#auth-password", Input)
        submit_btn = self.query_one("#auth-btn-submit", Button)

        username_input.value = ""
        password_input.value = ""
        username_input.display = True
        password_input.display = True
        submit_btn.display = True
        username_input.focus()
        status.update("Sign up: choose username and password, then Submit.")

    @on(Button.Pressed, "#auth-btn-submit")
    def handle_auth_submit(self) -> None:
        """Handle login/signup submission from the sidebar inputs."""
        status = self.query_one("#status", Label)
        user_label = self.query_one("#user-label", Label)
        username_input = self.query_one("#auth-username", Input)
        password_input = self.query_one("#auth-password", Input)
        submit_btn = self.query_one("#auth-btn-submit", Button)
        auth_screen = self.query_one("#auth-screen", Container)
        app_screen = self.query_one("#app-screen", Container)

        mode = self._auth_mode
        if mode is None:
            status.update("Choose Login or Sign Up first.")
            return

        username = username_input.value.strip()
        password = password_input.value

        if not username or not password:
            status.update("Username and password are required.")
            return

        if mode == "signup":
            ok, error = create_user(username, password)
            if not ok:
                status.update(error or "Could not create user.")
                return
            self._current_user = username
            # Initialize consent tool scoped to this user and load existing consent if any.
            self._consent_tool = ConsentTool(username=username)
            self._consent_tool.load_existing_consent()
            user_label.update(f"User: {username}")
            status.update(f"Account created. Logged in as {username}.")
        else:
            ok, error = authenticate_user(username, password)
            if not ok:
                status.update(error or "Login failed.")
                return
            self._current_user = username
            self._consent_tool = ConsentTool(username=username)
            self._consent_tool.load_existing_consent()
            user_label.update(f"User: {username}")
            status.update(f"Logged in as {username}.")

        # Hide auth UI after successful auth and show main app screen
        username_input.display = False
        password_input.display = False
        submit_btn.display = False
        self._auth_mode = None
        auth_screen.display = False
        app_screen.display = True

    @on(Button.Pressed, "#btn-analyze")
    def handle_analyze_zip(self) -> None:
        status = self.query_one("#status", Label)

        try:
            if self._current_user is None:
                status.update("Please log in before analyzing.")
                return

            # Ensure we have a consent tool scoped to the current user and
            # attempt to load any existing consent configuration.
            if self._consent_tool is None or self._consent_tool.username != self._current_user:
                self._consent_tool = ConsentTool(username=self._current_user)
                # If loading fails, fall back to requiring explicit
                # configuration via the dedicated button.
                with suppress(Exception):
                    self._consent_tool.load_existing_consent()

            # Do NOT open the consent GUI from here; that can appear as a hang
            # inside the TUI. Require users to configure consent explicitly.
            if self._consent_tool is None or not self._consent_tool.consent_given:
                status.update("Consent not configured. Use 'Configure Consent' before analyzing.")
                return

            status.update("Select a ZIP file to analyze...")

            selected = prompt_for_zip_file()
            if selected is None:
                status.update("No file selected.")
                return

            if not selected.exists() or not selected.is_file():
                status.update("Invalid file.")
                return

            self._run_analysis(selected)
        except Exception as exc:  # pragma: no cover - defensive
            import traceback

            traceback.print_exc()
            status.update(f"Error during Analyze ZIP: {exc}")

    @on(Button.Pressed, "#btn-retrieve")
    def handle_retrieve_projects(self) -> None:
        """List persisted uploads/projects/analyses from the database.

        This action intentionally does not prompt for a ZIP. Use
        "Analyze ZIP" when you want to upload and analyze a new archive.
        """
        status = self.query_one("#status", Label)
        if self._current_user is None:
            status.update("Please log in before retrieving saved analyses.")
            return

        status.update("Querying saved uploads...")

        try:
            self._run_list_saved()
        except Exception as exc:
            status.update(f"Error querying saved uploads: {exc}")

    @on(Button.Pressed, "#btn-skills")
    def handle_view_skills(self) -> None:
        """
        Lists the users aggregated skills from across
        all their stored projects.
        """

        status = self.query_one("#status", Label)

        if self._current_user is None:
            status.update("Please login before viewing skills.")
            return

        try:
            from capstone_project_team_5.data.db import get_session
            from capstone_project_team_5.data.models import User

            with get_session() as session:
                user = (
                    session.query(User).filter(User.username == self._current_user.strip()).first()
                )

                if user is None:
                    status.update("User not found.")
                    return

                skills = get_chronological_skills(session=session, user_id=user.id)

            md = render_skills_as_markdown(skills)
            self._current_markdown = md
            self.query_one("#output", Markdown).update(md)
            self._reset_analysis_selection_ui()
            status.update(f"Showing {len(skills)} skill(s).")

        except Exception as e:
            status.update(f"Error fetching skills: {e}")

    @on(Button.Pressed, "#btn-delete-analysis")
    def handle_delete_analysis(self) -> None:
        """Delete the currently selected code analysis."""
        status = self.query_one("#status", Label)
        analysis_list = self.query_one("#analysis-list", ListView)

        if not self._analysis_selected:
            status.update("No analysis selected to delete.")
            return

        if self._saved_active_project_index is None:
            status.update("Please select a project first.")
            return

        if analysis_list.index is None or analysis_list.index < 0:
            status.update("Please select an analysis to delete.")
            return

        project = self._saved_projects[self._saved_active_project_index]
        analyses = project.get("analyses") or []
        if analysis_list.index >= len(analyses):
            status.update("Invalid analysis selection.")
            return

        analysis = analyses[analysis_list.index]
        analysis_id = analysis.get("id")
        if analysis_id is None:
            status.update("Cannot delete: analysis ID not found.")
            return

        # Delete the analysis from database
        from capstone_project_team_5.services.code_analysis_persistence import (
            delete_code_analysis,
        )

        if delete_code_analysis(analysis_id):
            status.update(f"Deleted analysis {analysis_id}.")
            # Clear selection state and hide button
            self._reset_analysis_selection_ui()
            # Refresh the saved projects list
            try:
                self._run_list_saved()
            except Exception as exc:
                status.update(f"Analysis deleted but error refreshing list: {exc}")
        else:
            status.update(f"Failed to delete analysis {analysis_id}.")

    @on(Button.Pressed, "#btn-set-thumbnail")
    def handle_set_thumbnail(self) -> None:
        """Attach or clear a thumbnail image for the selected saved project."""

        status = self.query_one("#status", Label)
        if self._view_mode != "saved":
            status.update("Switch to saved view to set a thumbnail.")
            return
        if self._current_user is None:
            status.update("Please log in to set a thumbnail.")
            return

        project_id = self._current_saved_project_id()
        if project_id is None:
            status.update("Select a saved project first.")
            return

        if has_project_thumbnail(project_id):
            if clear_project_thumbnail(project_id):
                status.update("Thumbnail cleared.")
                if self._saved_active_project_index is not None:
                    self._show_saved_project(self._saved_active_project_index)
            else:
                status.update("No thumbnail to clear or operation failed.")
            return

        selected = self._prompt_for_thumbnail_file()
        if selected is None:
            status.update("Thumbnail selection cancelled.")
            return
        if not selected.exists() or not selected.is_file():
            status.update("Invalid thumbnail file.")
            return

        data = selected.read_bytes()
        saved, error = set_project_thumbnail(
            project_id,
            filename=selected.name,
            content_type=None,
            data=data,
        )
        if saved:
            status.update("Thumbnail set.")
            if self._saved_active_project_index is not None:
                self._show_saved_project(self._saved_active_project_index)
        else:
            status.update(error or "Failed to set thumbnail.")

    @on(Button.Pressed, "#btn-load-latest")
    def handle_load_latest_saved(self) -> None:
        """Load the latest saved analysis for the current user into project view."""
        status = self.query_one("#status", Label)
        if self._current_user is None:
            status.update("Please log in before loading saved analyses.")
            return

        status.update("Loading latest saved analysis...")

        try:
            self._run_load_latest_saved()
        except Exception as exc:  # pragma: no cover - defensive
            status.update(f"Error loading latest analysis: {exc}")

    # ---------------------------------------------------------------------
    # WORKER
    # ---------------------------------------------------------------------

    def _run_analysis(self, zip_path: Path) -> None:
        project_list = self.query_one("#project-list", ListView)
        analysis_list = self.query_one("#analysis-list", ListView)
        output = self.query_one("#output", Markdown)
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)

        # Switch to live analysis mode.
        self._view_mode = "analysis"
        self._analysis_selected = False
        self._update_thumbnail_buttons(None)
        analysis_list.display = False
        analysis_list.clear()
        project_list.display = True
        project_list.clear()
        output.update("")
        progress.update(progress=5)
        status.update("Uploading ZIP...")

        # Hide delete button when switching to analysis mode
        self._reset_analysis_selection_ui()

        tool = self._consent_tool or ConsentTool()

        def work() -> dict:
            import tempfile
            from zipfile import ZipFile

            result = upload_zip(zip_path)

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                with ZipFile(zip_path) as archive:
                    archive.extractall(tmp)

                project_analyses = analyze_projects_structured(
                    tmp, result.projects, tool, self._current_user
                )

            return {
                "upload": {
                    "filename": result.filename,
                    "size_bytes": result.size_bytes,
                    "file_count": result.file_count,
                },
                "projects": project_analyses,
            }

        self._worker = self.run_worker(
            work, name="analysis", exclusive=True, thread=True, exit_on_error=False
        )

    def _run_retrieve(self, zip_path: Path) -> None:
        output = self.query_one("#output", Markdown)
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)

        output.update("")
        progress.update(progress=5)
        status.update("Retrieving projects...")
        self._update_thumbnail_buttons(None)

        def work() -> dict:
            result = upload_zip(zip_path)

            detected = [
                {"name": p.name, "rel_path": p.rel_path, "file_count": p.file_count}
                for p in result.projects
            ]

            return {"detected": detected}

        self._worker = self.run_worker(
            work, name="retrieve", exclusive=True, thread=True, exit_on_error=False
        )

    def _run_list_saved(self) -> None:
        """Background worker to query persisted uploads/projects/analyses from the DB."""
        project_list = self.query_one("#project-list", ListView)
        analysis_list = self.query_one("#analysis-list", ListView)
        output = self.query_one("#output", Markdown)
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)

        self._view_mode = "saved"
        self._analysis_selected = False
        self._update_thumbnail_buttons(None)
        project_list.display = True
        analysis_list.display = True
        project_list.clear()
        analysis_list.clear()
        output.update("")
        progress.update(progress=5)
        status.update("Querying saved uploads...")

        # Hide delete button initially (until an analysis is selected)
        self._reset_analysis_selection_ui()

        def work() -> dict:
            # Import inside worker to avoid top-level DB dependency in the UI thread
            import json

            from capstone_project_team_5.data.db import get_session
            from capstone_project_team_5.data.models import (
                CodeAnalysis,
                Project,
                UploadRecord,
                User,
                UserCodeAnalysis,
            )

            results: list[dict] = []
            current_username = self._current_user

            with get_session() as session:
                user = None
                if current_username is not None:
                    user = (
                        session.query(User)
                        .filter(User.username == current_username.strip())
                        .first()
                    )

                # If we have a logged-in user, restrict uploads to those where
                # they have at least one linked analysis. Otherwise, show all.
                if user is not None:
                    uploads = (
                        session.query(UploadRecord)
                        .join(Project, Project.upload_id == UploadRecord.id)
                        .join(CodeAnalysis, CodeAnalysis.project_id == Project.id)
                        .join(
                            UserCodeAnalysis,
                            UserCodeAnalysis.analysis_id == CodeAnalysis.id,
                        )
                        .filter(UserCodeAnalysis.user_id == user.id)
                        .order_by(UploadRecord.created_at.desc())
                        .distinct()
                        .all()
                    )
                else:
                    uploads = (
                        session.query(UploadRecord).order_by(UploadRecord.created_at.desc()).all()
                    )

                for up in uploads:
                    upd: dict = {
                        "id": up.id,
                        "filename": up.filename,
                        "size_bytes": up.size_bytes,
                        "file_count": up.file_count,
                        "created_at": str(up.created_at),
                        "projects": [],
                    }
                    for p in up.projects:
                        # Aggregate fields across any saved analyses for this project,
                        # restricted to the current user when available.
                        languages: set[str] = set()
                        tools: set[str] = set()
                        practices: set[str] = set()
                        total_loc: int = 0
                        analyses_list: list[dict] = []

                        for a in p.code_analyses:
                            if user is not None:
                                link = (
                                    session.query(UserCodeAnalysis)
                                    .filter(
                                        UserCodeAnalysis.user_id == user.id,
                                        UserCodeAnalysis.analysis_id == a.id,
                                    )
                                    .first()
                                )
                                if link is None:
                                    continue

                            # Try to parse stored metrics JSON for structured info
                            metrics: dict | None = None
                            from contextlib import suppress

                            if getattr(a, "metrics_json", None):
                                with suppress(Exception):
                                    metrics = json.loads(a.metrics_json)

                            lang = None
                            metrics_tools: list = []
                            metrics_practices: list = []
                            loc = None
                            if isinstance(metrics, dict):
                                lang = metrics.get("language") or metrics.get("language_name")
                                metrics_tools = metrics.get("tools") or []
                                metrics_practices = metrics.get("practices") or []
                                loc = metrics.get("lines_of_code") or metrics.get(
                                    "total_lines_of_code"
                                )

                            if a.language:
                                languages.add(a.language)
                            if lang:
                                languages.add(lang)

                            for t in metrics_tools:
                                tools.add(str(t))
                            for pr in metrics_practices:
                                practices.add(str(pr))

                            try:
                                if isinstance(loc, int):
                                    total_loc += loc
                                elif isinstance(loc, str) and loc.isdigit():
                                    total_loc += int(loc)
                            except Exception:
                                pass

                            analyses_list.append(
                                {
                                    "id": a.id,
                                    "language": a.language,
                                    "summary_text": a.summary_text,
                                    "created_at": str(a.created_at),
                                }
                            )

                        # Only keep projects that have at least one analysis
                        # linked for this user (or any user when no login).
                        if not analyses_list:
                            continue

                        proj = {
                            "id": p.id,
                            "name": p.name,
                            "rel_path": p.rel_path,
                            "file_count": p.file_count,
                            "importance_rank": p.importance_rank,
                            "importance_score": p.importance_score,
                            "analyses": analyses_list,
                            "languages": sorted(languages),
                            "tools": sorted(tools),
                            "practices": sorted(practices),
                            "lines_of_code": total_loc if total_loc > 0 else None,
                            "analyses_count": len(analyses_list),
                        }

                        upd["projects"].append(proj)

                    if upd["projects"]:
                        results.append(upd)

            return {"saved": results}

        self._worker = self.run_worker(
            work, name="saved_list", exclusive=True, thread=True, exit_on_error=False
        )

    def _run_load_latest_saved(self) -> None:
        """Background worker to load the latest saved upload into project view."""
        project_list = self.query_one("#project-list", ListView)
        output = self.query_one("#output", Markdown)
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)

        project_list.display = True
        project_list.clear()
        output.update("")
        progress.update(progress=5)
        status.update("Loading latest saved analysis...")
        self._view_mode = "saved"
        self._update_thumbnail_buttons(None)

        current_username = self._current_user

        def work() -> dict:
            import json

            from capstone_project_team_5.data.db import get_session
            from capstone_project_team_5.data.models import (
                CodeAnalysis,
                Project,
                UploadRecord,
                User,
                UserCodeAnalysis,
            )

            if current_username is None:
                return {"upload": None, "projects": []}

            with get_session() as session:
                user = session.query(User).filter(User.username == current_username.strip()).first()
                if user is None:
                    return {"upload": None, "projects": []}

                uploads = (
                    session.query(UploadRecord)
                    .join(Project)
                    .join(CodeAnalysis)
                    .join(
                        UserCodeAnalysis,
                        UserCodeAnalysis.analysis_id == CodeAnalysis.id,
                    )
                    .filter(UserCodeAnalysis.user_id == user.id)
                    .order_by(UploadRecord.created_at.desc())
                    .all()
                )

                if not uploads:
                    return {"upload": None, "projects": []}

                upload = uploads[0]
                projects = (
                    session.query(Project)
                    .filter(Project.upload_id == upload.id)
                    .order_by(Project.id.asc())
                    .all()
                )

                project_dicts: list[dict] = []

                for proj in projects:
                    # Latest analysis for this project and user
                    ca = (
                        session.query(CodeAnalysis)
                        .join(
                            UserCodeAnalysis,
                            UserCodeAnalysis.analysis_id == CodeAnalysis.id,
                        )
                        .filter(
                            CodeAnalysis.project_id == proj.id,
                            UserCodeAnalysis.user_id == user.id,
                        )
                        .order_by(CodeAnalysis.created_at.desc())
                        .first()
                    )
                    if ca is None:
                        continue

                    metrics: dict = {}
                    if getattr(ca, "metrics_json", None):
                        try:
                            metrics = json.loads(ca.metrics_json)
                        except Exception:  # pragma: no cover - defensive
                            metrics = {}

                    language = (
                        metrics.get("language")
                        or metrics.get("language_name")
                        or ca.language
                        or "Unknown"
                    )
                    framework = metrics.get("framework")
                    tools = set(metrics.get("tools", []))
                    practices = set(metrics.get("practices", []))

                    total_files = (
                        metrics.get("total_files")
                        or metrics.get("total_files_count")
                        or proj.file_count
                        or 0
                    )

                    file_summary = {
                        "total_files": int(total_files),
                        "total_size": "Unknown (loaded from saved analysis)",
                    }

                    project_dicts.append(
                        {
                            "name": proj.name,
                            "rel_path": proj.rel_path,
                            "language": language,
                            "framework": framework,
                            "other_languages": [],
                            "practices": sorted(practices),
                            "tools": sorted(tools),
                            "duration": "Unknown (loaded from saved analysis)",
                            "duration_timedelta": None,
                            "collaborators_display": "",
                            "collaborators_raw": {
                                "count": 0,
                                "identities": [],
                            },
                            "file_summary": file_summary,
                            "contribution": {
                                "metrics": None,
                                "source": "saved",
                            },
                            "contribution_summary": "Loaded from saved analysis.",
                            "score": proj.importance_score or 0.0,
                            "score_breakdown": {},
                            "ai_bullets": [],
                            "ai_warning": None,
                            "resume_bullets": [],
                            "resume_bullet_source": "saved",
                            "skill_timeline": [],
                            "git": {
                                "is_repo": proj.has_git_repo,
                                "current_author": None,
                                "author_contributions": [],
                                "current_author_contribution": None,
                                "activity_chart": [],
                            },
                        }
                    )

                if not project_dicts:
                    return {"upload": None, "projects": []}

                upload_summary = {
                    "filename": upload.filename,
                    "size_bytes": upload.size_bytes,
                    "file_count": upload.file_count,
                }

                return {"upload": upload_summary, "projects": project_dicts}

        self._worker = self.run_worker(
            work, name="load_latest", exclusive=True, thread=True, exit_on_error=False
        )

    def _save_current_edit_to_db(self, edited_markdown: str) -> bool:
        """Save edited markdown to database."""

        from capstone_project_team_5.services.portfolio import save_portfolio_item

        if self._saved_active_project_index is None:
            return False

        project = self._saved_projects[self._saved_active_project_index]
        project_id = project.get("id")

        if project_id is None or self._current_user is None:
            return False

        return save_portfolio_item(
            self._current_user, project_id, project["name"], edited_markdown, is_user_edited=True
        )

    # ---------------------------------------------------------------------
    # WORKER STATE HANDLER
    # ---------------------------------------------------------------------

    @on(Worker.StateChanged)
    def worker_state(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._worker:
            return

        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)
        output = self.query_one("#output", Markdown)

        if event.state == WorkerState.RUNNING:
            progress.update(progress=40)
            if event.worker.name == "saved_list":
                status.update("Loading saved analyses...")
            elif event.worker.name == "retrieve":
                status.update("Retrieving projects...")
            else:
                status.update("Analyzing...")
            return

        if event.state == WorkerState.SUCCESS:
            data = event.worker.result

            if event.worker.name in {"analysis", "load_latest"}:
                self._handle_worker_success_analysis_like(
                    data=data, worker_name=str(event.worker.name), progress=progress, status=status
                )
                return

            if event.worker.name == "saved_list":
                self._handle_worker_success_saved_list(
                    data=data, progress=progress, status=status, output=output
                )
                return

            if event.worker.name == "retrieve":
                self._handle_worker_success_retrieve(
                    data=data, progress=progress, status=status, output=output
                )
                return

        if event.state == WorkerState.ERROR:
            status.update(f"Error: {event.worker.error}")
            progress.update(progress=0)

        if event.state == WorkerState.CANCELLED:
            status.update("Cancelled.")
            progress.update(progress=0)

    def _handle_worker_success_analysis_like(
        self,
        *,
        data: dict,
        worker_name: str,
        progress: ProgressBar,
        status: Label,
    ) -> None:
        """Handle successful completion of analysis or load_latest workers."""
        upload = data.get("upload")
        projects = data.get("projects") or []

        if not upload or not projects:
            progress.update(progress=0)
            msg = (
                "No saved analyses found."
                if worker_name == "load_latest"
                else "No projects analyzed."
            )
            status.update(msg)
            return

        self._upload_summary = upload
        self._projects = projects

        if worker_name == "analysis":
            status.update("Analysis complete.")
        else:
            status.update("Loaded latest saved analysis.")

        progress.update(progress=100)

        project_list = self.query_one("#project-list", ListView)
        project_list.clear()

        if not self._projects:
            return

        indexed_scores = [(i, proj.get("score", 0.0)) for i, proj in enumerate(self._projects)]
        ranked = sorted(indexed_scores, key=lambda pair: pair[1], reverse=True)
        current_rank = 1
        previous_score: float | None = None
        self._ranks = {}
        for position, (idx, score) in enumerate(ranked):
            if previous_score is not None and score < previous_score:
                current_rank = position + 1
            self._ranks[idx] = current_rank
            previous_score = score

        for idx, proj in enumerate(self._projects):
            rank = self._ranks.get(idx)
            score = proj.get("score")
            label = proj["name"]
            if rank is not None:
                label = f"#{rank} {label}"
            if score is not None:
                label = f"{label} (score {score:.1f})"
            project_list.append(ListItem(Label(label)))

        project_list.index = 0
        self._show_project_detail(0)

    def _handle_worker_success_saved_list(
        self,
        *,
        data: dict,
        progress: ProgressBar,
        status: Label,
        output: Markdown,
    ) -> None:
        """Handle successful completion of the saved_list worker."""
        progress.update(progress=100)
        saved = data.get("saved") or []

        self._saved_uploads = saved
        self._saved_projects = []
        self._saved_active_project_index = None

        project_list = self.query_one("#project-list", ListView)
        analysis_list = self.query_one("#analysis-list", ListView)
        project_list.clear()
        analysis_list.clear()

        for up in saved:
            upload_name = up.get("filename")
            upload_id = up.get("id")
            for p in up.get("projects", []):
                proj = dict(p)
                proj["upload_filename"] = upload_name
                proj["upload_id"] = upload_id
                self._saved_projects.append(proj)

        if not self._saved_projects:
            status.update("No saved uploads found for this user.")
            output.update("# Saved Uploads\n\n(No saved uploads found)")
            return

        for proj in self._saved_projects:
            label = f"{proj.get('upload_filename')} / {proj.get('name')}"
            project_list.append(ListItem(Label(label)))

        project_list.index = 0
        self._saved_active_project_index = 0
        self._show_saved_project(0)
        self._update_thumbnail_buttons(self._current_saved_project_id())
        status.update("Loaded saved analyses.")

    def _handle_worker_success_retrieve(
        self,
        *,
        data: dict,
        progress: ProgressBar,
        status: Label,
        output: Markdown,
    ) -> None:
        """Handle successful completion of the retrieve worker."""
        progress.update(progress=100)
        status.update("Retrieve complete.")
        detected = data.get("detected") or []
        md = render_detected_list(detected)
        self._current_markdown = md
        output.update(md)

    # ---------------------------------------------------------------------
    # PROJECT DETAIL RENDERING
    # ---------------------------------------------------------------------

    @on(ListView.Selected, "#project-list")
    def handle_project_selected(self, event: ListView.Selected) -> None:
        """Update detail pane when the user selects a project in the list."""
        if self._view_mode == "saved":
            # Hide delete button when switching projects (no analysis selected yet)
            self._reset_analysis_selection_ui()

            self._saved_active_project_index = event.index
            self._update_thumbnail_buttons(self._current_saved_project_id())
            self._show_saved_project(event.index)
        else:
            self._show_project_detail(event.index)

    @on(ListView.Selected, "#analysis-list")
    def handle_saved_analysis_selected(self, event: ListView.Selected) -> None:
        """Render an individual saved analysis snapshot with detailed metrics."""
        if self._view_mode != "saved":
            return
        if self._saved_active_project_index is None:
            return
        if self._saved_active_project_index < 0 or self._saved_active_project_index >= len(
            self._saved_projects
        ):
            return

        project = self._saved_projects[self._saved_active_project_index]
        project_id = project.get("id")
        analyses = project.get("analyses") or []
        if not analyses or event.index < 0 or event.index >= len(analyses):
            return

        # Show delete button when an analysis is selected
        self._analysis_selected = True
        delete_btn = self.query_one("#btn-delete-analysis", Button)
        delete_btn.display = True

        # Show export buttons when analysis is selected
        export_pdf_btn = self.query_one("#btn-export-pdf", Button)
        export_txt_btn = self.query_one("#btn-export-txt", Button)
        export_pdf_btn.display = True
        export_txt_btn.display = True

        analysis = analyses[event.index]

        analysis_id = analysis.get("id")
        if analysis_id is None:
            return

        status = self.query_one("#status", Label)
        portfolio_item = None

        if self._current_user and project_id:
            from capstone_project_team_5.services.portfolio import get_portfolio_item

            candidate = get_portfolio_item(self._current_user, project_id)
            # Only treat a portfolio item as an edited analysis version
            # when it is explicitly linked to this analysis via
            # source_analysis_id. This avoids showing unrelated
            # project-level portfolio content for every analysis.
            if candidate and candidate.get("source_analysis_id") == analysis_id:
                portfolio_item = candidate

        if portfolio_item is not None:
            status.update("Retrieved portfolio item.")
            # Show user's edited version
            title = portfolio_item["title"]
            raw_content = portfolio_item["content"]
            content = self._extract_markdown_from_portfolio_content(raw_content) or str(raw_content)
            updated = portfolio_item["updated_at"].strftime("%Y-%m-%d %H:%M")

            analysis_lang = analysis.get("language", "Unknown")
            analysis_date = analysis.get("created_at", "Unknown")

            md = (
                f"# {title}\n\n"
                f"**[✏️ User Edited - {updated}]**\n\n"
                f"*Viewing edited version for analysis: {analysis_lang} @ {analysis_date}*\n\n"
                f"{content}"
            )
        else:
            # Fetch full CodeAnalysis + metrics from the database for this snapshot.
            try:
                import json

                from capstone_project_team_5.data.db import get_session
                from capstone_project_team_5.data.models import CodeAnalysis, Project

                with get_session() as session:
                    ca = session.query(CodeAnalysis).filter(CodeAnalysis.id == analysis_id).first()
                    if ca is None:
                        summary_text = analysis.get("summary_text") or "(no summary available)"
                        md = f"# Saved Analysis\n\n{summary_text}"
                    else:
                        metrics: dict | None = None
                        if getattr(ca, "metrics_json", None):
                            try:
                                metrics = json.loads(ca.metrics_json)
                            except Exception:  # pragma: no cover - defensive
                                metrics = None

                        proj_row = (
                            session.query(Project)
                            .filter(Project.id == getattr(ca, "project_id", -1))
                            .first()
                        )

                        md = self._render_saved_analysis_detail(
                            project_dict=project,
                            analysis_row=ca,
                            metrics=metrics or {},
                            project_row=proj_row,
                        )
            except Exception:
                summary_text = analysis.get("summary_text") or "(no summary available)"
                md = f"# Saved Analysis\n\n{summary_text}"

        self._current_markdown = md
        self.query_one("#output", Markdown).update(md)

    def _show_saved_project(self, index: int) -> None:
        """Populate analyses list and summary for a saved project."""
        if not self._saved_projects:
            return
        if index < 0 or index >= len(self._saved_projects):
            return

        project = self._saved_projects[index]
        self._update_thumbnail_buttons(project.get("id"))
        analysis_list = self.query_one("#analysis-list", ListView)
        output = self.query_one("#output", Markdown)

        analyses = project.get("analyses") or []

        analysis_list.clear()
        for a in analyses:
            label = f"{a.get('language')} @ {a.get('created_at')}"
            analysis_list.append(ListItem(Label(label)))

        # Prefer a saved portfolio markdown for this project if available.
        custom_markdown = self._get_saved_project_portfolio_markdown(project)
        if custom_markdown is not None:
            md = custom_markdown
        else:
            # Show a brief project summary in the markdown pane.
            parts: list[str] = []
            parts.append("# Saved Project\n")
            parts.append(
                f"## {project.get('name')}  \n"
                f"`{project.get('rel_path')}` (Upload: {project.get('upload_filename')})\n"
            )
            parts.append(f"- Files: {project.get('file_count')}")
            parts.append(f"- Upload ID: {project.get('upload_id')}")
            langs = project.get("languages") or []
            if langs:
                parts.append(f"- Languages: {', '.join(langs)}")
            practices = project.get("practices") or []
            tools = project.get("tools") or []
            skills = practices + tools
            if skills:
                parts.append(f"- Skills (Tools/Practices): {', '.join(skills[:12])}")
            loc = project.get("lines_of_code")
            if loc is not None:
                parts.append(f"- Lines of code (sum of analyses): {loc}")
            parts.append(self._thumbnail_status_line(project.get("id")))

            parts.append("")
            if analyses:
                parts.append("Select an analysis on the left to view its detailed summary.")
            else:
                parts.append("No analyses have been saved for this project yet.")

            md = "\n".join(parts)

        self._current_markdown = md
        output.update(md)

    def _render_saved_analysis_detail(
        self,
        *,
        project_dict: dict[str, object],
        analysis_row: CodeAnalysis,
        metrics: dict[str, object],
        project_row: Project | None = None,
    ) -> str:
        """Render detailed markdown for a saved analysis snapshot."""
        parts: list[str] = []

        title = project_dict.get("upload_filename") or "Saved Analysis"
        parts.append(f"# {title}\n")

        parts.append(
            f"## {project_dict.get('name')}  \n"
            f"`{project_dict.get('rel_path')}` "
            f"(Upload ID: {project_dict.get('upload_id')})\n"
        )

        parts.append("### Summary")
        parts.append(f"- Analysis ID: {analysis_row.id}")
        parts.append(f"- Timestamp: {analysis_row.created_at}")

        language = (
            metrics.get("language")
            or metrics.get("language_name")
            or getattr(analysis_row, "language", None)
            or "Unknown"
        )
        project_languages = project_dict.get("languages") or []
        if not isinstance(project_languages, (list, tuple)):
            project_languages = []
        normalized_project_langs = [
            str(lang).strip() for lang in project_languages if str(lang).strip()
        ]

        # Fallback: if language is still unknown, try aggregated project languages.
        if (
            (not isinstance(language, str)) or not language.strip() or language == "Unknown"
        ) and normalized_project_langs:
            language = normalized_project_langs[0]
        framework = metrics.get("framework")
        parts.append(f"- Language: {language}")
        if normalized_project_langs:
            parts.append(f"- Project languages: {', '.join(sorted(set(normalized_project_langs)))}")
        parts.append(f"- Framework: {framework or 'None detected'}")

        total_files = (
            metrics.get("total_files")
            or metrics.get("total_files_count")
            or project_dict.get("file_count")
            or 0
        )
        parts.append(f"- Files: {int(total_files)}")

        loc = metrics.get("lines_of_code") or metrics.get("total_lines_of_code")
        if isinstance(loc, int):
            parts.append(f"- Lines of code: {loc}")

        if project_row is not None and project_row.importance_score is not None:
            parts.append(f"- Importance score: {project_row.importance_score:.1f}")

        # Skills and tools
        tools = set(metrics.get("tools", []))
        practices = set(metrics.get("practices", []))

        parts.append("\n### Skills - Practices")
        if practices:
            parts.extend(f"- {s}" for s in sorted(practices))
        else:
            # Fall back to aggregated skills from project_dict if any.
            fallback_practices = project_dict.get("practices") or []
            if fallback_practices:
                parts.extend(f"- {s}" for s in fallback_practices)
            else:
                parts.append("- None detected")

        parts.append("\n### Skills - Tools")
        if tools:
            parts.extend(f"- {t}" for t in sorted(tools))
        else:
            # Fall back to aggregated tools from project_dict if any.
            fallback_tools = project_dict.get("tools") or []
            if fallback_tools:
                parts.extend(f"- {t}" for t in fallback_tools)
            else:
                parts.append("- None detected")

        # Generic metrics (if present)
        oop_score = metrics.get("oop_score")
        complexity_score = metrics.get("complexity_score")
        if oop_score is not None or complexity_score is not None:
            parts.append("\n### Code Quality Metrics")
            if oop_score is not None:
                parts.append(f"- OOP score: {oop_score}")
            if complexity_score is not None:
                parts.append(f"- Complexity score: {complexity_score}")

        # Lightweight resume-style bullets reconstructed from saved metrics.
        bullets: list[str] = []
        if language != "Unknown":
            if framework:
                bullets.append(
                    f"Built a {language} project using {framework} with approximately "
                    f"{int(total_files)} files."
                )
            else:
                bullets.append(
                    f"Built a {language} project with approximately {int(total_files)} files."
                )
        if tools:
            top_tools = ", ".join(sorted(tools)[:5])
            bullets.append(f"Used tools and technologies such as {top_tools}.")
        if practices:
            top_practices = ", ".join(sorted(practices)[:8])
            bullets.append(f"Demonstrated skills in {top_practices}.")
        if isinstance(loc, int) and loc > 0:
            bullets.append(f"Worked with roughly {loc} lines of code in this snapshot.")

        parts.append("\n### Resume Bullet Points (from saved analysis)")
        if bullets:
            parts.extend(f"- {b}" for b in bullets)
        else:
            parts.append("- Not enough data to infer bullet points.")

        # Original summary text
        summary = analysis_row.summary_text or "(no summary available)"
        parts.append("\n### Summary Text")
        parts.append(summary)

        return "\n".join(parts)

    def _extract_markdown_from_portfolio_content(self, raw: str) -> str | None:
        """Extract a markdown string from stored portfolio content.

        Content is stored as JSON; we accept either a plain string or an
        object with a ``\"markdown\"`` field.
        """
        try:
            import json

            decoded = json.loads(raw)
        except Exception:
            decoded = raw

        if isinstance(decoded, dict):
            markdown = decoded.get("markdown")
            if isinstance(markdown, str) and markdown.strip():
                return markdown
            return None

        if isinstance(decoded, str) and decoded.strip():
            return decoded

        return None

    def _get_saved_project_portfolio_markdown(self, project: dict[str, object]) -> str | None:
        """Return saved portfolio markdown for a project in the saved view, if any."""
        project_id = project.get("id")
        if not isinstance(project_id, int):
            return None

        try:
            item = get_latest_portfolio_item_for_project(project_id)
        except Exception:
            return None

        if item is None:
            return None

        return self._extract_markdown_from_portfolio_content(item.content)

    def _get_analysis_project_portfolio_markdown(self, project: dict[str, object]) -> str | None:
        """Return saved portfolio markdown for a project in analysis view, if any."""
        name = project.get("name")
        rel_path = project.get("rel_path")
        if not isinstance(name, str) or not isinstance(rel_path, str):
            return None

        try:
            from capstone_project_team_5.data.db import get_session
            from capstone_project_team_5.data.models import Project as ProjectModel

            with get_session() as session:
                proj_row = (
                    session.query(ProjectModel)
                    .filter(ProjectModel.name == name, ProjectModel.rel_path == rel_path)
                    .first()
                )

                if proj_row is None:
                    return None

                item = get_latest_portfolio_item_for_project(proj_row.id)
        except Exception:
            return None

        if item is None:
            return None

        return self._extract_markdown_from_portfolio_content(item.content)

    def _show_project_detail(self, index: int) -> None:
        """Render details for a single selected project into the markdown view."""
        if not self._projects or self._upload_summary is None:
            return
        if index < 0 or index >= len(self._projects):
            return

        proj = self._projects[index]
        # Always render the latest analysis summary for this project.
        rank = self._ranks.get(index)
        md = render_project_markdown(self._upload_summary, proj, rank)
        self._current_markdown = md
        self.query_one("#output", Markdown).update(md)

    # ---------------------------------------------------------------------
    # EDIT MODE ACTIONS
    # ---------------------------------------------------------------------

    @on(Button.Pressed, "#btn-config")
    def handle_config_button(self) -> None:
        """Re-run the consent/config sequence on demand."""
        status = self.query_one("#status", Label)

        # Hide delete button when switching to config
        self._reset_analysis_selection_ui()

        if self._current_user is None:
            status.update("Please log in before configuring consent.")
            return

        tool = self._consent_tool or ConsentTool(username=self._current_user)
        if not tool.generate_consent_form():
            status.update("Consent configuration cancelled; previous settings kept.")
            return

        self._consent_tool = tool
        status.update("Consent configuration updated.")

    @on(Button.Pressed, "#btn-edit")
    def handle_edit_button(self) -> None:
        # Hide delete button when switching to edit view
        self._reset_analysis_selection_ui()
        self.action_toggle_edit()

    @on(Button.Pressed, "#btn-export-pdf")
    def handle_export_pdf_button(self) -> None:
        """Handle Export PDF button press."""
        self._do_export_direct("pdf")

    @on(Button.Pressed, "#btn-export-txt")
    def handle_export_txt_button(self) -> None:
        """Handle Export TXT button press."""
        self._do_export_direct("txt")

    def _get_current_project_name(self) -> str | None:
        """Get the name of the currently selected project for export filename."""
        if (
            self._view_mode == "saved"
            and self._saved_active_project_index is not None
            and 0 <= self._saved_active_project_index < len(self._saved_projects)
        ):
            return self._saved_projects[self._saved_active_project_index].get("name")
        return None

    def _export_analysis(self, export_format: str) -> None:
        """Export current analysis to the specified format.

        Args:
            export_format: Either "pdf" or "txt"
        """
        status = self.query_one("#status", Label)

        if not self._current_markdown.strip():
            status.update("Nothing to export. Select an analysis first.")
            return

        if self._view_mode != "saved" or not self._analysis_selected:
            status.update("Export is only available for saved analyses.")
            return

        status.update(f"Select save location for {export_format.upper()}...")

        # Schedule the blocking dialog to run after the current event completes
        # This allows the TUI to update before the blocking call
        self.call_later(self._do_export, export_format)

    def _do_export_direct(self, export_format: str) -> None:
        """Export directly from button press (like prompt_for_zip_file pattern).

        Args:
            export_format: Either "pdf" or "txt"
        """
        import easygui

        status = self.query_one("#status", Label)

        if not self._current_markdown.strip():
            status.update("Nothing to export. Select an analysis first.")
            return

        if self._view_mode != "saved" or not self._analysis_selected:
            status.update("Export is only available for saved analyses.")
            return

        # Import export utilities
        from capstone_project_team_5.utils.export import (
            _generate_filename,
            export_to_pdf,
            export_to_txt,
        )

        project_name = self._get_current_project_name()
        filename = _generate_filename(project_name, export_format)

        status.update(f"Select save location for {export_format.upper()}...")

        # Call dialog directly like prompt_for_zip_file does
        result = easygui.filesavebox(
            msg=f"Save {export_format.upper()} file",
            title=f"Export Analysis as {export_format.upper()}",
            default=filename,
            filetypes=[f"*.{export_format}"],
        )

        if result is None:
            status.update("Export cancelled.")
            return

        output_path = Path(result)

        # Ensure correct extension
        if output_path.suffix.lower() != f".{export_format}":
            output_path = output_path.with_suffix(f".{export_format}")

        status.update(f"Writing {export_format.upper()} file...")

        try:
            if export_format == "pdf":
                export_to_pdf(self._current_markdown, output_path)
            else:
                export_to_txt(self._current_markdown, output_path)
            status.update(f"Exported to: {output_path}")
        except Exception as e:
            status.update(f"Export error: {e}")

    def _do_export(self, export_format: str) -> None:
        """Perform the actual export after dialog selection.

        Args:
            export_format: Either "pdf" or "txt"
        """
        status = self.query_one("#status", Label)

        # Import export utilities
        from capstone_project_team_5.utils.export import (
            _generate_filename,
            export_to_pdf,
            export_to_txt,
            prompt_export_location,
        )

        project_name = self._get_current_project_name()
        filename = _generate_filename(project_name, export_format)

        # Prompt for location - this blocks but TUI has already updated
        output_path = prompt_export_location(filename)

        if output_path is None:
            status.update("Export cancelled.")
            return

        # Ensure correct extension
        if output_path.suffix.lower() != f".{export_format}":
            output_path = output_path.with_suffix(f".{export_format}")

        status.update(f"Writing {export_format.upper()} file...")

        try:
            if export_format == "pdf":
                export_to_pdf(self._current_markdown, output_path)
            else:
                export_to_txt(self._current_markdown, output_path)
            status.update(f"Exported to: {output_path}")
        except Exception as e:
            status.update(f"Export error: {e}")

    def action_export_pdf(self) -> None:
        """Export current analysis as PDF."""
        self._export_analysis("pdf")

    def action_export_txt(self) -> None:
        """Export current analysis as TXT."""
        self._export_analysis("txt")

    def action_toggle_edit(self) -> None:
        """Toggle between view and edit modes."""
        output = self.query_one("#output", Markdown)
        editor = self.query_one("#editor", TextArea)
        status = self.query_one("#status", Label)

        if editor.display:
            # Already editing: cancel
            editor.display = False
            output.display = True
            status.update("Edit cancelled.")
            return

        # No analysis rendered yet – nothing to edit
        if not self._current_markdown.strip():
            status.update("Nothing to edit yet. Run an analysis first.")
            return

        editor.load_text(self._current_markdown)
        editor.display = True
        output.display = False
        editor.focus()
        status.update("Edit mode: Ctrl+S to save, Esc to cancel.")

    def action_save_edit(self) -> None:
        """Save edits back into the Markdown view."""
        output = self.query_one("#output", Markdown)
        editor = self.query_one("#editor", TextArea)
        status = self.query_one("#status", Label)

        if not editor.display:
            return

        self._current_markdown = editor.text
        output.update(self._current_markdown)
        editor.display = False
        output.display = True

        if self._view_mode == "saved" and self._saved_active_project_index is not None:
            try:
                self._persist_saved_project_portfolio()
                status.update("Edits saved to portfolio.")
            except Exception as exc:  # pragma: no cover - defensive
                status.update(f"Edits saved locally, but failed to persist: {exc}")
        elif self._view_mode == "analysis":
            try:
                self._persist_analysis_project_portfolio()
                status.update("Edits saved to portfolio.")
            except Exception as exc:  # pragma: no cover - defensive
                status.update(f"Edits saved locally, but failed to persist: {exc}")
        else:
            status.update("Edits saved.")

    def action_cancel_edit(self) -> None:
        """Cancel edit mode without saving changes."""
        output = self.query_one("#output", Markdown)
        editor = self.query_one("#editor", TextArea)
        status = self.query_one("#status", Label)

        if not editor.display:
            return

        editor.display = False
        output.display = True
        status.update("Edit cancelled.")

    def _persist_saved_project_portfolio(self) -> None:
        """Persist the current markdown as a portfolio item for the active saved project."""
        if self._current_user is None or self._saved_active_project_index is None:
            return
        if self._saved_active_project_index < 0 or self._saved_active_project_index >= len(
            self._saved_projects
        ):
            return

        project = self._saved_projects[self._saved_active_project_index]
        project_id = project.get("id")
        if not isinstance(project_id, int):
            return

        title_obj = project.get("name") or "Project Showcase"
        title = str(title_obj)

        try:
            # If an analysis is selected, treat this as an edited
            # analysis-level portfolio entry and link it to the
            # specific CodeAnalysis via source_analysis_id. This
            # ensures the edited text is shown only for that
            # analysis when revisiting the saved view.
            analysis_list = self.query_one("#analysis-list", ListView)
            analyses = project.get("analyses") or []
            analysis_id: int | None = None
            if analysis_list.index is not None and 0 <= analysis_list.index < len(analyses):
                selected = analyses[analysis_list.index]
                selected_id = selected.get("id")
                if isinstance(selected_id, int):
                    analysis_id = selected_id

            if analysis_id is not None:
                import json

                from capstone_project_team_5.services.portfolio import save_portfolio_item

                save_portfolio_item(
                    username=self._current_user,
                    project_id=project_id,
                    title=title,
                    content=json.dumps({"markdown": self._current_markdown}),
                    is_user_edited=True,
                    is_showcase=False,
                    source_analysis_id=analysis_id,
                )
            else:
                # No analysis selected – persist a project‑level portfolio item.
                create_portfolio_item(
                    username=self._current_user,
                    project_id=project_id,
                    title=title,
                    content={"markdown": self._current_markdown},
                )
        except Exception:
            return

    def _persist_analysis_project_portfolio(self) -> None:
        """Persist the current markdown as a portfolio item for the active analysis project."""
        project_list = self.query_one("#project-list", ListView)
        index = project_list.index
        if index is None:
            return
        if index < 0 or index >= len(self._projects):
            return

        project = self._projects[index]
        name = project.get("name")
        rel_path = project.get("rel_path")
        if self._current_user is None or not isinstance(name, str) or not isinstance(rel_path, str):
            return

        try:
            from capstone_project_team_5.data.db import get_session
            from capstone_project_team_5.data.models import Project as ProjectModel

            with get_session() as session:
                proj_row = (
                    session.query(ProjectModel)
                    .filter(ProjectModel.name == name, ProjectModel.rel_path == rel_path)
                    .first()
                )
                if proj_row is None:
                    return

            title_obj = project.get("name") or "Project Showcase"
            title = str(title_obj)

            create_portfolio_item(
                username=self._current_user,
                project_id=proj_row.id,
                title=title,
                content={"markdown": self._current_markdown},
            )
        except Exception:
            return

    @on(Button.Pressed, "#btn-logout")
    def handle_logout(self) -> None:
        """Log out current user and return to auth screen."""
        self._current_user = None
        self._auth_mode = None
        status = self.query_one("#status", Label)
        user_label = self.query_one("#user-label", Label)
        auth_screen = self.query_one("#auth-screen", Container)
        app_screen = self.query_one("#app-screen", Container)
        project_list = self.query_one("#project-list", ListView)
        output = self.query_one("#output", Markdown)
        progress = self.query_one("#progress", ProgressBar)

        user_label.update("Hi, -")
        project_list.clear()
        output.update("")
        progress.update(progress=0)
        auth_screen.display = True
        app_screen.display = False
        status.update("Logged out. Please log in again.")
        self._update_thumbnail_buttons(None)

    @on(Button.Pressed, "#btn-exit")
    def exit_app(self) -> None:
        self.exit()


def main() -> None:
    Zip2JobTUI().run()

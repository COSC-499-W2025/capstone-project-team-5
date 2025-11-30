from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    Markdown,
    ProgressBar,
    Static,
    TextArea,
)
from textual.worker import Worker, WorkerState

from capstone_project_team_5.cli import analyze_projects_structured
from capstone_project_team_5.consent_tool import ConsentTool
from capstone_project_team_5.services import upload_zip
from capstone_project_team_5.utils import prompt_for_zip_file


class Zip2JobTUI(App[None]):
    """Modern, scrollable TUI for Zip2Job."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("e", "toggle_edit", "Edit view"),
        ("ctrl+s", "save_edit", "Save edit"),
        ("escape", "cancel_edit", "Cancel edit"),
    ]

    CSS = """
Screen {
    layout: vertical;
    background: $background;
}

/* Top: header stays default */

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

    def compose(self) -> ComposeResult:
        yield Header()

        yield Container(
            # Middle region: sidebar + main scroll area
            Container(
                # Sidebar
                Container(
                    Static("Zip2Job\nAnalyzer", id="title"),
                    Button("Analyze ZIP", id="btn-analyze", variant="primary"),
                    Button("Retrieve Projects", id="btn-retrieve", variant="secondary"),
                    Button("Edit View", id="btn-edit", variant="default"),
                    Button("Exit", id="btn-exit", variant="error"),
                    id="sidebar",
                ),
                # Main area
                Container(
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
                id="middle",
            ),
            # Status bar
            Container(
                Label("Ready.", id="status"),
                ProgressBar(total=100, id="progress"),
                id="statusbar",
            ),
        )

        yield Footer()

    def on_mount(self) -> None:
        editor = self.query_one("#editor", TextArea)
        editor.display = False

    # ---------------------------------------------------------------------
    # EVENTS
    # ---------------------------------------------------------------------

    @on(Button.Pressed, "#btn-analyze")
    def handle_analyze_zip(self) -> None:
        status = self.query_one("#status", Label)
        status.update("Requesting consent...")

        if self._consent_tool is None:
            tool = ConsentTool()
            if not tool.generate_consent_form():
                status.update("Consent denied.")
                return
            self._consent_tool = tool

        selected = prompt_for_zip_file()
        if selected is None:
            status.update("No file selected.")
            return

        if not selected.exists() or not selected.is_file():
            status.update("Invalid file.")
            return

        self._run_analysis(selected)

    @on(Button.Pressed, "#btn-retrieve")
    def handle_retrieve_projects(self) -> None:
        status = self.query_one("#status", Label)
        status.update("Requesting consent for retrieval...")

        if self._consent_tool is None:
            tool = ConsentTool()
            if not tool.generate_consent_form():
                status.update("Consent denied.")
                return
            self._consent_tool = tool

        selected = prompt_for_zip_file()
        if selected is None:
            status.update("No file selected.")
            return

        if not selected.exists() or not selected.is_file():
            status.update("Invalid file.")
            return

        self._run_retrieve(selected)

    # ---------------------------------------------------------------------
    # WORKER
    # ---------------------------------------------------------------------

    def _run_analysis(self, zip_path: Path) -> None:
        output = self.query_one("#output", Markdown)
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)

        output.update("")
        progress.update(progress=5)
        status.update("Uploading ZIP...")

        tool = self._consent_tool or ConsentTool()

        def work() -> dict:
            import tempfile
            from zipfile import ZipFile

            result = upload_zip(zip_path)

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                with ZipFile(zip_path) as archive:
                    archive.extractall(tmp)

                project_analyses = analyze_projects_structured(tmp, result.projects, tool)

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

        tool = self._consent_tool or ConsentTool()

        def work() -> dict:
            import tempfile
            from zipfile import ZipFile

            result = upload_zip(zip_path)

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                with ZipFile(zip_path) as archive:
                    archive.extractall(tmp)

                project_analyses = analyze_projects_structured(tmp, result.projects, tool)

            return {"projects": project_analyses}

        self._worker = self.run_worker(
            work, name="retrieve", exclusive=True, thread=True, exit_on_error=False
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
            status.update("Analyzing...")
            return

        if event.state == WorkerState.SUCCESS:
            progress.update(progress=100)
            status.update("Analysis complete.")

            data = event.worker.result
            projects = data.get("projects")
            upload = data.get("upload")

            if upload:
                md = self._render_markdown(upload, projects)
                self._current_markdown = md
                output.update(md)
            else:
                table = self._render_table(projects or [])
                self._current_markdown = table
                output.update(table)
            return

        if event.state == WorkerState.ERROR:
            status.update(f"Error: {event.worker.error}")
            progress.update(progress=0)

        if event.state == WorkerState.CANCELLED:
            status.update("Cancelled.")
            progress.update(progress=0)

    # ---------------------------------------------------------------------
    # MARKDOWN RENDERING
    # ---------------------------------------------------------------------

    def _render_markdown(self, upload, projects) -> str:
        parts = []

        parts.append(f"# {upload['filename']}\n")

        parts.append("## Upload Summary")
        parts.append(f"- **Size**: {upload['size_bytes']:,} bytes")
        parts.append(f"- **Files**: {upload['file_count']}")
        parts.append(f"- **Projects detected**: {len(projects)}\n")

        # Projects
        if projects:
            parts.append("\n## Projects")
            for proj in projects:
                parts.append(f"\n### {proj['name']}  \n`{proj['rel_path']}`")
                parts.append(f"- Duration: {proj['duration']}")
                parts.append(f"- Language: {proj['language']}")
                parts.append(f"- Framework: {proj['framework']}")
                parts.append(
                    f"- Files: {proj['file_summary']['total_files']} "
                    f"({proj['file_summary']['total_size']})"
                )

                parts.append("\n**Skills**")
                parts.extend(f"- {s}" for s in proj["skills"])

                parts.append("\n**Tools**")
                parts.extend(f"- {t}" for t in proj["tools"])

                if proj["ai_bullets"]:
                    parts.append("\n**AI Bullet Points**")
                    parts.extend(f"- {b}" for b in proj["ai_bullets"])
                elif proj["ai_warning"]:
                    parts.append(f"\n> {proj['ai_warning']}")

        return "\n".join(parts)

    def _render_table(self, projects: list[dict]) -> str:
        """Render a simple ASCII table summary for retrieved projects."""
        headers = ["Name", "Path", "Language", "Framework", "Duration", "Files", "Skills", "Tools"]
        rows: list[list[str]] = []
        for p in projects:
            name = str(p.get("name", ""))
            rel = str(p.get("rel_path", ""))
            lang = str(p.get("language", ""))
            fw = str(p.get("framework", ""))
            duration = str(p.get("duration", ""))
            files = str(p.get("file_summary", {}).get("total_files", ""))
            skills = ",".join(p.get("skills", []))
            tools = ",".join(p.get("tools", []))
            rows.append([name, rel, lang, fw, duration, files, skills, tools])

        col_widths = [len(h) for h in headers]
        for r in rows:
            for i, cell in enumerate(r):
                col_widths[i] = max(col_widths[i], len(cell))

        def fmt_row(row: list[str]) -> str:
            return " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))

        sep = "-+-".join("-" * w for w in col_widths)
        lines = [fmt_row(headers), sep]
        for r in rows:
            lines.append(fmt_row(r))

        return "```\n" + "\n".join(lines) + "\n```"

    # ---------------------------------------------------------------------
    # EDIT MODE ACTIONS
    # ---------------------------------------------------------------------

    @on(Button.Pressed, "#btn-edit")
    def handle_edit_button(self) -> None:
        self.action_toggle_edit()

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

    @on(Button.Pressed, "#btn-exit")
    def exit_app(self) -> None:
        self.exit()


def main() -> None:
    Zip2JobTUI().run()

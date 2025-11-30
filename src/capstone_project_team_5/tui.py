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
                    Button("Retrieve Projects", id="btn-retrieve", variant="default"),
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
        """List persisted uploads/projects/analyses from the database.

        This action intentionally does not prompt for a ZIP. Use
        "Analyze ZIP" when you want to upload and analyze a new archive.
        """
        status = self.query_one("#status", Label)
        status.update("Querying saved uploads...")

        try:
            self._run_list_saved()
        except Exception as exc:
            status.update(f"Error querying saved uploads: {exc}")

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

            # Local imports to avoid heavy top-level dependencies in the UI
            from capstone_project_team_5.services.project_analysis import analyze_project
            from capstone_project_team_5.services.code_analysis_persistence import (
                save_code_analysis_to_db,
            )

            result = upload_zip(zip_path)

            saved_count = 0
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp = Path(tmpdir)
                with ZipFile(zip_path) as archive:
                    archive.extractall(tmp)

                # Compute structured analyses for UI display
                project_analyses = analyze_projects_structured(tmp, result.projects, tool)

                # Persist language-specific analyses for each detected project.
                # This is best-effort: failures are ignored per-project to avoid
                # aborting the whole worker.
                for proj_meta in result.projects:
                    try:
                        # Resolve project path within the extraction dir
                        proj_path = (
                            tmp.joinpath(*proj_meta.rel_path.split("/"))
                            if proj_meta.rel_path
                            else tmp
                        )
                        if not proj_path.exists() or not proj_path.is_dir():
                            continue

                        analysis = analyze_project(proj_path)

                        try:
                            save_code_analysis_to_db(proj_meta.name, proj_meta.rel_path, analysis)
                            saved_count += 1
                        except Exception:
                            # Ignore DB save errors for robustness
                            pass
                    except Exception:
                        # Ignore per-project analysis errors
                        continue

            return {
                "upload": {
                    "filename": result.filename,
                    "size_bytes": result.size_bytes,
                    "file_count": result.file_count,
                },
                "projects": project_analyses,
                "saved_count": saved_count,
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
        output = self.query_one("#output", Markdown)
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)

        output.update("")
        progress.update(progress=5)
        status.update("Querying saved uploads...")

        def work() -> dict:
            # Import inside worker to avoid top-level DB dependency in the UI thread
            import json

            from capstone_project_team_5.data.db import get_session
            from capstone_project_team_5.data.models import UploadRecord

            results: list[dict] = []
            with get_session() as session:
                uploads = session.query(UploadRecord).order_by(UploadRecord.created_at.desc()).all()

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
                        # Aggregate fields across any saved analyses for this project
                        languages: set[str] = set()
                        skills: set[str] = set()
                        total_loc: int = 0
                        analyses_list: list[dict] = []

                        for a in p.code_analyses:
                            # Try to parse stored metrics JSON for structured info
                            metrics: dict | None = None
                            try:
                                if getattr(a, "metrics_json", None):
                                    metrics = json.loads(a.metrics_json)
                            except Exception:
                                metrics = None

                            lang = None
                            if isinstance(metrics, dict):
                                lang = metrics.get("language") or metrics.get("language_name")
                                tools = metrics.get("tools") or []
                                practices = metrics.get("practices") or []
                                loc = metrics.get("lines_of_code") or metrics.get(
                                    "total_lines_of_code"
                                )
                            else:
                                tools = []
                                practices = []
                                loc = None

                            if a.language:
                                languages.add(a.language)
                            if lang:
                                languages.add(lang)

                            for t in tools:
                                try:
                                    skills.add(str(t))
                                except Exception:
                                    pass
                            for pr in practices:
                                try:
                                    skills.add(str(pr))
                                except Exception:
                                    pass

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

                        proj = {
                            "id": p.id,
                            "name": p.name,
                            "rel_path": p.rel_path,
                            "file_count": p.file_count,
                            "importance_rank": p.importance_rank,
                            "importance_score": p.importance_score,
                            "analyses": analyses_list,
                            "languages": sorted(languages),
                            "skills": sorted(skills),
                            "lines_of_code": total_loc if total_loc > 0 else None,
                            "analyses_count": len(analyses_list),
                        }

                        upd["projects"].append(proj)

                    results.append(upd)

            return {"saved": results}

        self._worker = self.run_worker(
            work, name="saved_list", exclusive=True, thread=True, exit_on_error=False
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
            upload = data.get("upload")
            detected = data.get("detected")
            saved = data.get("saved")
            projects = data.get("projects")

            if upload:
                md = self._render_markdown(upload, projects)
                self._current_markdown = md
                output.update(md)
                # If we saved analyses to the DB, show a brief status note
                saved_count = data.get("saved_count")
                if isinstance(saved_count, int) and saved_count > 0:
                    status.update(f"Analysis complete. Persisted {saved_count} analyses.")
                return

            if detected is not None:
                md = self._render_detected_list(detected)
                self._current_markdown = md
                output.update(md)
                return

            if saved is not None:
                md = self._render_saved_list(saved)
                self._current_markdown = md
                output.update(md)
                return

            # fallback: render full project analyses table if present
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

    def _render_detected_list(self, detected: list[dict]) -> str:
        """Render a simple markdown list of detected projects (name + rel_path)."""
        parts: list[str] = ["# Detected Projects", ""]
        if not detected:
            parts.append("(No projects detected)")
            return "\n".join(parts)

        for p in detected:
            name = p.get("name", "<unnamed>")
            rel = p.get("rel_path", "")
            files = p.get("file_count", "?")
            parts.append(f"- **{name}** — `{rel}` ({files} files)")

        return "\n".join(parts)

    def _render_saved_list(self, saved: list[dict]) -> str:
        """Render persisted uploads, their projects, and any saved analyses."""
        parts: list[str] = ["# Saved Uploads", ""]
        if not saved:
            parts.append("(No saved uploads found)")
            return "\n".join(parts)

        for up in saved:
            parts.append(f"## Upload: {up.get('filename')}  ")
            parts.append(f"- **ID**: {up.get('id')}  ")
            parts.append(f"- **Files**: {up.get('file_count')}  ")
            parts.append(f"- **Size**: {up.get('size_bytes'):,} bytes  ")
            parts.append(f"- **Created**: {up.get('created_at')}  ")
            projects = up.get("projects", [])
            if not projects:
                parts.append("- (No projects recorded for this upload)")
                parts.append("")
                continue

            parts.append("")
            parts.append("### Projects")
            for p in projects:
                parts.append(
                    f"- **{p.get('name')}** — `{p.get('rel_path')}` ({p.get('file_count')} files)"
                )
                if p.get("importance_rank") is not None:
                    parts.append(
                        f"  - Rank: {p.get('importance_rank')} — Score: {p.get('importance_score')}"
                    )

                # Languages / skills / LOC summary
                langs = p.get("languages") or []
                if langs:
                    parts.append(f"  - Languages: {', '.join(langs)}")
                skills = p.get("skills") or []
                if skills:
                    parts.append(f"  - Skills/Tools: {', '.join(skills[:12])}")
                loc = p.get("lines_of_code")
                if loc is not None:
                    parts.append(f"  - Lines of code (sum of analyses): {loc}")

                analyses = p.get("analyses", [])
                if analyses:
                    parts.append(f"  - Analyses ({p.get('analyses_count', len(analyses))}):")
                    for a in analyses:
                        txt = a.get("summary_text") or "(no summary)"
                        parts.append(
                            f"    - {a.get('language')} @ {a.get('created_at')}: {txt[:120]}"
                        )

            parts.append("")

        return "\n".join(parts)

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

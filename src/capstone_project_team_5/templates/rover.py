"""Rover resume template.

Faithfully based on ``github.com/subidit/rover-resume`` — uppercase bold
section headers with horizontal rules, native LaTeX sectioning,
1-inch margins on A4, ``description`` list for skills.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pylatex import Document, NoEscape, Package

from capstone_project_team_5.templates.base import ResumeTemplate

if TYPE_CHECKING:
    from capstone_project_team_5.services.resume_data import (
        ResumeData,
        ResumeEducationEntry,
        ResumeProjectEntry,
        ResumeWorkEntry,
    )

__all__ = ["RoverResumeTemplate"]

# ---------------------------------------------------------------------------
# LaTeX preamble fragments
# ---------------------------------------------------------------------------

_PACKAGES: list[Package] = [
    Package("geometry", options=NoEscape("a4paper,margin=1in")),
    Package("titlesec"),
    Package("enumitem"),
    Package("hyperref", options=NoEscape("hidelinks")),
    Package("fontenc", options=NoEscape("T1")),
]

_PREAMBLE_SETUP = r"""
\setlength{\parindent}{0pt}
\setcounter{secnumdepth}{0}
\titleformat{\section}{\large\bfseries\uppercase}{}{}{}[\titlerule]
\titleformat{\subsection}{\bfseries}{}{0em}{}
\titleformat*{\subsubsection}{\itshape}
\titlespacing{\section}{0pt}{6pt}{4pt}
\titlespacing{\subsection}{0pt}{4pt}{0pt}
\titlespacing{\subsubsection}{0pt}{2pt}{0pt}
\setlist[itemize]{noitemsep, topsep=2pt, left=0pt .. 1.5em}
\setlist[description]{itemsep=0pt}
\pagestyle{empty}
\pdfgentounicode=1
"""


class RoverResumeTemplate(ResumeTemplate):
    """Rover-style ATS-friendly resume with uppercase section headers."""

    @property
    def name(self) -> str:  # pragma: no cover
        return "Rover Resume"

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def build(self, data: ResumeData) -> Document:
        doc = self._create_document()
        self._add_heading(doc, data.get("contact", {}))

        education = data.get("education", [])
        if education:
            self._add_education(doc, education)

        work = data.get("work_experience", [])
        if work:
            self._add_experience(doc, work)

        projects = data.get("projects", [])
        if projects:
            self._add_projects(doc, projects)

        skills = data.get("skills", {})
        if skills.get("tools") or skills.get("practices"):
            self._add_skills(doc, skills)

        return doc

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _create_document(self) -> Document:
        doc = Document(
            documentclass="article",
            document_options=["a4paper", "11pt"],
            page_numbers=True,
            indent=True,
            lmodern=False,
            textcomp=False,
            microtype=False,
            fontenc=None,
            inputenc=None,
        )
        doc.packages = [p for p in doc.packages if "lastpage" not in p.dumps()]

        for pkg in _PACKAGES:
            doc.packages.append(pkg)
        doc.preamble.append(NoEscape(_PREAMBLE_SETUP))
        return doc

    # -- heading -----------------------------------------------------------

    def _add_heading(self, doc: Document, contact: dict) -> None:
        esc = self.escape_latex
        name = esc(contact.get("name", ""))

        # Right-side contact info
        parts: list[str] = []
        phone = contact.get("phone")
        if phone:
            parts.append(esc(phone))
        email = contact.get("email")
        if email:
            parts.append(rf"\href{{mailto:{email}}}{{{esc(email)}}}")
        linkedin = contact.get("linkedin_url")
        if linkedin:
            display = self._strip_protocol(linkedin)
            parts.append(rf"\href{{{linkedin}}}{{{esc(display)}}}")
        github = contact.get("github_url")
        if github:
            display = self._strip_protocol(github)
            parts.append(rf"\href{{{github}}}{{{esc(display)}}}")
        website = contact.get("website_url")
        if website:
            display = self._strip_protocol(website)
            parts.append(rf"\href{{{website}}}{{{esc(display)}}}")

        heading = r"\begin{center}" "\n"
        heading += r"\begin{minipage}[t]{0.5\textwidth}" "\n"
        heading += rf"{{\Huge\bfseries {name}}}" "\n"
        heading += r"\end{minipage}%" "\n"
        heading += r"\hfill" "\n"
        heading += r"\begin{minipage}[t]{0.4\textwidth}" "\n"
        heading += r"\raggedleft" "\n"
        if parts:
            heading += r" \\ ".join(parts) + "\n"
        heading += r"\end{minipage}" "\n"
        heading += r"\end{center}"
        doc.append(NoEscape(heading))

    # -- education ---------------------------------------------------------

    def _add_education(
        self,
        doc: Document,
        entries: list[ResumeEducationEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Education}"]

        for entry in entries:
            institution = esc(entry.get("institution", ""))
            degree = esc(entry.get("degree", ""))
            field = entry.get("field_of_study", "")
            if field:
                degree = f"{degree} in {esc(field)}"
            date_range = self.format_date_range(
                entry.get("start_date"),
                entry.get("end_date"),
                entry.get("is_current", False),
            )

            # Double-line header: institution/location, degree/dates
            lines.append(
                rf"\subsection*{{{institution}"
                rf" $|$ {{\normalfont\itshape {degree}}} \hfill {date_range}}}"
            )

            gpa = entry.get("gpa")
            achievements = entry.get("achievements", [])
            if gpa is not None or achievements:
                lines.append(r"\begin{itemize}")
                if gpa is not None:
                    lines.append(rf"\item GPA: {gpa:.2f}")
                for ach in achievements:
                    lines.append(rf"\item {esc(ach)}")
                lines.append(r"\end{itemize}")

        doc.append(NoEscape("\n".join(lines)))

    # -- experience --------------------------------------------------------

    def _add_experience(
        self,
        doc: Document,
        entries: list[ResumeWorkEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Experience}"]

        for entry in entries:
            company = esc(entry.get("company", ""))
            title = esc(entry.get("title", ""))
            location = esc(entry.get("location", ""))
            date_range = self.format_date_range(
                entry.get("start_date"),
                entry.get("end_date"),
                entry.get("is_current", False),
            )

            lines.append(rf"\subsection*{{{company} \hfill {location}}}")
            lines.append(rf"\subsubsection*{{{title} \hfill {date_range}}}")

            bullets = entry.get("bullets", [])
            if bullets:
                lines.append(r"\begin{itemize}")
                for bullet in bullets:
                    lines.append(rf"\item {esc(bullet)}")
                lines.append(r"\end{itemize}")

        doc.append(NoEscape("\n".join(lines)))

    # -- projects ----------------------------------------------------------

    def _add_projects(
        self,
        doc: Document,
        entries: list[ResumeProjectEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Projects}"]

        for entry in entries:
            name = esc(entry.get("name", ""))
            techs = entry.get("technologies", [])
            tech_str = rf" $|$ {{\normalfont\itshape {esc(', '.join(techs))}}}" if techs else ""
            date_range = self.format_date_range(
                entry.get("start_date"),
                entry.get("end_date"),
            )

            lines.append(rf"\subsection*{{{name}{tech_str} \hfill {date_range}}}")

            bullets = entry.get("bullets", [])
            if bullets:
                lines.append(r"\begin{itemize}")
                for bullet in bullets:
                    lines.append(rf"\item {esc(bullet)}")
                lines.append(r"\end{itemize}")

        doc.append(NoEscape("\n".join(lines)))

    # -- skills ------------------------------------------------------------

    def _add_skills(self, doc: Document, skills: dict) -> None:
        esc = self.escape_latex
        lines = [r"\section{Skills}", r"\begin{description}"]

        tools = skills.get("tools", [])
        practices = skills.get("practices", [])
        if tools:
            joined = esc(", ".join(tools))
            lines.append(rf"\item[Languages/Tools] {joined}")
        if practices:
            joined = esc(", ".join(practices))
            lines.append(rf"\item[Practices] {joined}")

        lines.append(r"\end{description}")
        doc.append(NoEscape("\n".join(lines)))

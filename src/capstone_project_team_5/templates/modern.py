"""Modern resume template.

Helvetica sans-serif, no decorative rules on section headers, compact
10pt body, tight margins.  Clean and dense single-page layout.
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

__all__ = ["ModernResumeTemplate"]

# ---------------------------------------------------------------------------
# LaTeX preamble fragments
# ---------------------------------------------------------------------------

_PACKAGES: list[Package] = [
    Package("latexsym"),
    Package("fullpage", options=NoEscape("empty")),
    Package("titlesec"),
    Package("enumitem"),
    Package("hyperref", options=NoEscape("hidelinks")),
    Package("fancyhdr"),
    Package("fontenc", options=NoEscape("T1")),
    Package("helvet"),
    Package("tabularx"),
]

_PREAMBLE_SETUP = r"""
\renewcommand{\familydefault}{\sfdefault}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\addtolength{\oddsidemargin}{-0.5in}
\addtolength{\evensidemargin}{-0.5in}
\addtolength{\textwidth}{1in}
\addtolength{\topmargin}{-.5in}
\addtolength{\textheight}{1.0in}
\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}
\setlength{\parindent}{0pt}
\titleformat{\section}{\large\bfseries}{}{0em}{}
\titlespacing{\section}{0pt}{8pt}{4pt}
\pdfgentounicode=1
"""

_CUSTOM_COMMANDS = r"""
\newcommand{\modernSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\modernItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}
\newcommand{\modernProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}
\newcommand{\modernListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\modernListEnd}{\end{itemize}}
\newcommand{\modernItemListStart}{\begin{itemize}[leftmargin=0.15in]}
\newcommand{\modernItemListEnd}{\end{itemize}\vspace{-5pt}}
"""


class ModernResumeTemplate(ResumeTemplate):
    """Modern sans-serif resume with compact layout."""

    @property
    def name(self) -> str:  # pragma: no cover
        return "Modern Resume"

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
            document_options=["letterpaper", "10pt"],
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
        doc.preamble.append(NoEscape(_CUSTOM_COMMANDS))
        return doc

    # -- heading -----------------------------------------------------------

    def _add_heading(self, doc: Document, contact: dict) -> None:
        esc = self.escape_latex
        name = esc(contact.get("name", ""))

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

        separator = r" \textbar\ "
        heading = r"\begin{center}"
        heading += rf"{{\Large\bfseries {name}}}"
        heading += r" \\ \vspace{1pt}"
        if parts:
            heading += rf"\small {separator.join(parts)}"
        heading += r"\end{center}"
        doc.append(NoEscape(heading))

    # -- education ---------------------------------------------------------

    def _add_education(
        self,
        doc: Document,
        entries: list[ResumeEducationEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Education}", r"\modernListStart"]

        for entry in entries:
            institution = esc(entry.get("institution", ""))
            degree = esc(entry.get("degree", ""))
            field = entry.get("field_of_study", "")
            if field:
                degree = f"{degree} in {esc(field)}"
            location = esc(entry.get("location", ""))
            date_range = self.format_date_range(
                entry.get("start_date"),
                entry.get("end_date"),
                entry.get("is_current", False),
            )
            lines.append(
                rf"\modernSubheading{{{institution}}}{{{location}}}{{{degree}}}{{{date_range}}}"
            )

            gpa = entry.get("gpa")
            achievements = entry.get("achievements", [])
            if gpa is not None or achievements:
                lines.append(r"\modernItemListStart")
                if gpa is not None:
                    lines.append(rf"\modernItem{{GPA: {gpa:.2f}}}")
                for ach in achievements:
                    lines.append(rf"\modernItem{{{esc(ach)}}}")
                lines.append(r"\modernItemListEnd")

        lines.append(r"\modernListEnd")
        doc.append(NoEscape("\n".join(lines)))

    # -- experience --------------------------------------------------------

    def _add_experience(
        self,
        doc: Document,
        entries: list[ResumeWorkEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Experience}", r"\modernListStart"]

        for entry in entries:
            company = esc(entry.get("company", ""))
            title = esc(entry.get("title", ""))
            location = esc(entry.get("location", ""))
            date_range = self.format_date_range(
                entry.get("start_date"),
                entry.get("end_date"),
                entry.get("is_current", False),
            )
            lines.append(
                rf"\modernSubheading{{{title}}}{{{date_range}}}{{{company}}}{{{location}}}"
            )

            bullets = entry.get("bullets", [])
            if bullets:
                lines.append(r"\modernItemListStart")
                for bullet in bullets:
                    lines.append(rf"\modernItem{{{esc(bullet)}}}")
                lines.append(r"\modernItemListEnd")

        lines.append(r"\modernListEnd")
        doc.append(NoEscape("\n".join(lines)))

    # -- projects ----------------------------------------------------------

    def _add_projects(
        self,
        doc: Document,
        entries: list[ResumeProjectEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Projects}", r"\modernListStart"]

        for entry in entries:
            name = esc(entry.get("name", ""))
            techs = entry.get("technologies", [])
            tech_str = r" $|$ \emph{" + esc(", ".join(techs)) + "}" if techs else ""
            date_range = self.format_date_range(
                entry.get("start_date"),
                entry.get("end_date"),
            )

            url = entry.get("url")
            if url:
                heading_text = rf"\textbf{{{name}}}{tech_str}"
                display_url = self._strip_protocol(url)
                heading_text += rf" $|$ \href{{{url}}}{{{esc(display_url)}}}"
            else:
                heading_text = rf"\textbf{{{name}}}{tech_str}"

            lines.append(rf"\modernProjectHeading{{{heading_text}}}{{{date_range}}}")

            bullets = entry.get("bullets", [])
            if bullets:
                lines.append(r"\modernItemListStart")
                for bullet in bullets:
                    lines.append(rf"\modernItem{{{esc(bullet)}}}")
                lines.append(r"\modernItemListEnd")

        lines.append(r"\modernListEnd")
        doc.append(NoEscape("\n".join(lines)))

    # -- skills ------------------------------------------------------------

    def _add_skills(self, doc: Document, skills: dict) -> None:
        esc = self.escape_latex
        lines = [
            r"\section{Skills}",
            r"\begin{itemize}[leftmargin=0.15in, label={}]",
            r"\small{\item{",
        ]

        tools = skills.get("tools", [])
        practices = skills.get("practices", [])
        if tools:
            joined = esc(", ".join(tools))
            suffix = r" \\" if practices else ""
            lines.append(rf"\textbf{{Tools}}{{: {joined}}}{suffix}")

        if practices:
            joined = esc(", ".join(practices))
            lines.append(rf"\textbf{{Practices}}{{: {joined}}}")

        lines.append(r"}}")
        lines.append(r"\end{itemize}")
        doc.append(NoEscape("\n".join(lines)))

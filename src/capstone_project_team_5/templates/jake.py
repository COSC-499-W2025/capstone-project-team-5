"""Jake Gutierrez resume template.

Reproduces the popular ATS-friendly single-page resume layout from
``github.com/jakegut/resume`` using PyLaTeX.
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

__all__ = ["JakeResumeTemplate"]

# ---------------------------------------------------------------------------
# LaTeX preamble fragments
# ---------------------------------------------------------------------------

_PACKAGES: list[Package] = [
    Package("latexsym"),
    Package("fullpage", options=NoEscape("empty")),
    Package("titlesec"),
    Package("marvosym"),
    Package("color", options=NoEscape("usenames,dvipsnames")),
    Package("verbatim"),
    Package("enumitem"),
    Package("hyperref", options=NoEscape("hidelinks")),
    Package("fancyhdr"),
    Package("babel", options=NoEscape("english")),
    Package("tabularx"),
    Package("fontenc", options=NoEscape("T1")),
]

_PREAMBLE_SETUP = r"""
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
\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-5pt}]
\pdfgentounicode=1
"""

_CUSTOM_COMMANDS = r"""
\newcommand{\resumeItem}[1]{
  \item\small{
    {#1 \vspace{-2pt}}
  }
}
\newcommand{\resumeSubheading}[4]{
  \vspace{-2pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubSubheading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \textit{\small#1} & \textit{\small #2} \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-7pt}
}
\newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}
\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}
\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{\begin{itemize}}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}
"""


class JakeResumeTemplate(ResumeTemplate):
    """Jake Gutierrez's ATS-friendly single-page resume."""

    @property
    def name(self) -> str:  # pragma: no cover
        return "Jake's Resume"

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
            document_options=["letterpaper", "11pt"],
            page_numbers=True,  # Jake's preamble uses fancyhdr
            indent=True,  # Jake's preamble sets \raggedright
            lmodern=False,
            textcomp=False,
            microtype=False,
            fontenc=None,
            inputenc=None,
        )
        # Remove lastpage auto-injected by page_numbers=True;
        # Jake's preamble handles page style via fancyhdr.
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
            parts.append(rf"\href{{mailto:{email}}}{{\underline{{{esc(email)}}}}}")
        linkedin = contact.get("linkedin_url")
        if linkedin:
            display = self._strip_protocol(linkedin)
            parts.append(rf"\href{{{linkedin}}}{{\underline{{{esc(display)}}}}}")
        github = contact.get("github_url")
        if github:
            display = self._strip_protocol(github)
            parts.append(rf"\href{{{github}}}{{\underline{{{esc(display)}}}}}")
        website = contact.get("website_url")
        if website:
            display = self._strip_protocol(website)
            parts.append(rf"\href{{{website}}}{{\underline{{{esc(display)}}}}}")

        separator = r" $|$ "
        heading = r"\begin{center}" rf"\textbf{{\Huge \scshape {name}}} \\ \vspace{{1pt}}"
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
        lines = [r"\section{Education}", r"\resumeSubHeadingListStart"]

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
                rf"\resumeSubheading{{{institution}}}{{{location}}}{{{degree}}}{{{date_range}}}"
            )

            # GPA + Achievements (must be inside a list environment)
            gpa = entry.get("gpa")
            achievements = entry.get("achievements", [])
            if gpa is not None or achievements:
                lines.append(r"\resumeItemListStart")
                if gpa is not None:
                    lines.append(rf"\resumeItem{{GPA: {gpa:.2f}}}")
                for ach in achievements:
                    lines.append(rf"\resumeItem{{{esc(ach)}}}")
                lines.append(r"\resumeItemListEnd")

        lines.append(r"\resumeSubHeadingListEnd")
        doc.append(NoEscape("\n".join(lines)))

    # -- experience --------------------------------------------------------

    def _add_experience(
        self,
        doc: Document,
        entries: list[ResumeWorkEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Experience}", r"\resumeSubHeadingListStart"]

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
                rf"\resumeSubheading{{{title}}}{{{date_range}}}{{{company}}}{{{location}}}"
            )

            bullets = entry.get("bullets", [])
            if bullets:
                lines.append(r"\resumeItemListStart")
                for bullet in bullets:
                    lines.append(rf"\resumeItem{{{esc(bullet)}}}")
                lines.append(r"\resumeItemListEnd")

        lines.append(r"\resumeSubHeadingListEnd")
        doc.append(NoEscape("\n".join(lines)))

    # -- projects ----------------------------------------------------------

    def _add_projects(
        self,
        doc: Document,
        entries: list[ResumeProjectEntry],
    ) -> None:
        esc = self.escape_latex
        lines = [r"\section{Projects}", r"\resumeSubHeadingListStart"]

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
                heading_text += rf" $|$ \href{{{url}}}{{\underline{{{esc(display_url)}}}}}"
            else:
                heading_text = rf"\textbf{{{name}}}{tech_str}"

            lines.append(rf"\resumeProjectHeading{{{heading_text}}}{{{date_range}}}")

            bullets = entry.get("bullets", [])
            if bullets:
                lines.append(r"\resumeItemListStart")
                for bullet in bullets:
                    lines.append(rf"\resumeItem{{{esc(bullet)}}}")
                lines.append(r"\resumeItemListEnd")

        lines.append(r"\resumeSubHeadingListEnd")
        doc.append(NoEscape("\n".join(lines)))

    # -- skills ------------------------------------------------------------

    def _add_skills(self, doc: Document, skills: dict) -> None:
        esc = self.escape_latex
        lines = [
            r"\section{Technical Skills}",
            r"\begin{itemize}[leftmargin=0.15in, label={}]",
            r"\small{\item{",
        ]

        tools = skills.get("tools", [])
        practices = skills.get("practices", [])
        if tools:
            joined = esc(", ".join(tools))
            suffix = r" \\" if practices else ""
            lines.append(rf"\textbf{{Languages/Tools}}{{: {joined}}}{suffix}")

        if practices:
            joined = esc(", ".join(practices))
            lines.append(rf"\textbf{{Practices}}{{: {joined}}}")

        lines.append(r"}}")
        lines.append(r"\end{itemize}")
        doc.append(NoEscape("\n".join(lines)))

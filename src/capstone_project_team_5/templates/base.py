"""Abstract base class for pluggable resume templates."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pylatex import Document

    from capstone_project_team_5.services.resume_data import ResumeData

__all__ = ["ResumeTemplate"]

# Characters that have special meaning in LaTeX.
_LATEX_SPECIAL = re.compile(r"([&%$#_{}])")
_LATEX_TILDE = re.compile(r"~")
_LATEX_CARET = re.compile(r"\^")
_LATEX_BACKSLASH = re.compile(r"\\")

_MONTH_ABBR = [
    "",
    "Jan.",
    "Feb.",
    "Mar.",
    "Apr.",
    "May",
    "Jun.",
    "Jul.",
    "Aug.",
    "Sep.",
    "Oct.",
    "Nov.",
    "Dec.",
]


class ResumeTemplate(ABC):
    """Interface that every resume template must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable template name shown in the UI."""

    @abstractmethod
    def build(self, data: ResumeData) -> Document:
        """Construct a PyLaTeX ``Document`` from *data*."""

    # ------------------------------------------------------------------
    # Shared helpers available to all templates
    # ------------------------------------------------------------------

    @staticmethod
    def escape_latex(text: str) -> str:
        r"""Escape LaTeX special characters in *text*.

        Handles: ``& % $ # _ { } ~ ^ \``
        """
        # Order matters: backslash first so we don't double-escape.
        result = _LATEX_BACKSLASH.sub(r"\\textbackslash{}", text)
        result = _LATEX_SPECIAL.sub(r"\\\1", result)
        result = _LATEX_TILDE.sub(r"\\textasciitilde{}", result)
        result = _LATEX_CARET.sub(r"\\textasciicircum{}", result)
        return result

    @staticmethod
    def format_date_range(
        start: str | None,
        end: str | None,
        is_current: bool = False,
    ) -> str:
        """Return a formatted date range like ``Aug. 2018 -- May 2021``.

        Dates are expected as ISO strings (``YYYY-MM-DD``).
        """

        def _fmt(iso: str | None) -> str:
            if not iso:
                return ""
            parts = iso.split("-")
            if len(parts) >= 2:
                month = int(parts[1])
                year = parts[0]
                return f"{_MONTH_ABBR[month]} {year}"
            return parts[0]

        start_str = _fmt(start)
        end_str = "Present" if is_current else _fmt(end)

        if start_str and end_str:
            return f"{start_str} -- {end_str}"
        return start_str or end_str or ""

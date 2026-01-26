"""Export utilities for converting markdown analysis to PDF and TXT formats."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fpdf import FPDF


def _sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")
    return sanitized or "analysis"


def _generate_filename(project_name: str | None, extension: str) -> str:
    """Generate a filename with timestamp.

    Args:
        project_name: Name of the project (optional)
        extension: File extension (pdf or txt)

    Returns:
        Filename string with timestamp
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base_name = _sanitize_filename(project_name or "analysis")
    return f"{base_name}_{timestamp}.{extension}"


def _strip_markdown_formatting(text: str) -> str:
    """Convert markdown to plain text for PDF rendering.

    Args:
        text: Markdown formatted text

    Returns:
        Plain text with markdown syntax removed
    """
    # Remove code blocks FIRST (before inline code, to avoid partial matching)
    text = re.sub(r"```[^\n]*\n[\s\S]*?```", "", text)

    # Remove headers but keep the text
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Remove bold/italic markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)

    # Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Remove links but keep text: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Clean up multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def export_to_txt(markdown_content: str, output_path: Path) -> Path:
    """Export markdown content to a plain text file.

    Args:
        markdown_content: The markdown content to export
        output_path: Full path for the output file

    Returns:
        Path to the created file
    """
    # For TXT, we strip markdown formatting for cleaner output
    plain_text = _strip_markdown_formatting(markdown_content)
    output_path.write_text(plain_text, encoding="utf-8")
    return output_path


def export_to_pdf(markdown_content: str, output_path: Path) -> Path:
    """Export markdown content to a PDF file.

    Args:
        markdown_content: The markdown content to export
        output_path: Full path for the output file

    Returns:
        Path to the created file
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Use built-in fonts (no external font files needed)
    pdf.set_font("Helvetica", size=11)

    def clean_text(text: str) -> str:
        """Remove markdown formatting and encode for PDF."""
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Replace any problematic unicode characters
        text = text.encode("latin-1", errors="replace").decode("latin-1")
        return text

    # Process markdown line by line
    lines = markdown_content.split("\n")

    for line in lines:
        stripped = line.strip()

        # Reset x position to left margin for each line
        pdf.set_x(pdf.l_margin)

        # Handle headers
        if stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.write(h=8, text=clean_text(stripped[4:]))
            pdf.ln(10)
            pdf.set_font("Helvetica", size=11)
        elif stripped.startswith("## "):
            pdf.ln(3)  # Add space before section
            pdf.set_font("Helvetica", "B", 14)
            pdf.write(h=10, text=clean_text(stripped[3:]))
            pdf.ln(12)
            pdf.set_font("Helvetica", size=11)
        elif stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.write(h=12, text=clean_text(stripped[2:]))
            pdf.ln(14)
            pdf.set_font("Helvetica", size=11)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            # Bullet point with text wrapping
            bullet_text = clean_text(stripped[2:])
            pdf.write(h=6, text=f"   - {bullet_text}")
            pdf.ln(8)
        elif stripped == "":
            # Empty line - add some spacing
            pdf.ln(4)
        else:
            # Regular text with wrapping
            pdf.write(h=6, text=clean_text(stripped))
            pdf.ln(8)

    pdf.output(str(output_path))
    return output_path


def prompt_export_location(default_filename: str) -> Path | None:
    """Prompt user to select export location using system file dialog.

    Args:
        default_filename: Suggested filename (extension determines file filter)

    Returns:
        Selected path or None if cancelled
    """
    import easygui

    # Build file type filter from extension
    extension = default_filename.rsplit(".", 1)[-1] if "." in default_filename else "pdf"
    filetypes = [f"*.{extension}"]

    result = easygui.filesavebox(
        msg="Choose export location",
        title="Export Analysis",
        default=default_filename,
        filetypes=filetypes,
    )

    if result:
        return Path(result)
    return None


def export_analysis(
    markdown_content: str,
    project_name: str | None = None,
    export_format: str = "pdf",
) -> Path | None:
    """Export analysis to file, prompting user for location.

    Args:
        markdown_content: The markdown content to export
        project_name: Name of the project for filename generation
        export_format: Either "pdf" or "txt"

    Returns:
        Path to created file, or None if cancelled
    """
    if not markdown_content.strip():
        return None

    filename = _generate_filename(project_name, export_format)
    output_path = prompt_export_location(filename)

    if output_path is None:
        return None

    # Ensure correct extension
    if output_path.suffix.lower() != f".{export_format}":
        output_path = output_path.with_suffix(f".{export_format}")

    if export_format == "pdf":
        return export_to_pdf(markdown_content, output_path)
    else:
        return export_to_txt(markdown_content, output_path)

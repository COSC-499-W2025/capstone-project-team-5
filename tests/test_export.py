"""Tests for the export utility module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from capstone_project_team_5.utils.export import (
    _generate_filename,
    _sanitize_filename,
    _strip_markdown_formatting,
    export_analysis,
    export_to_pdf,
    export_to_txt,
)


class TestSanitizeFilename:
    """Tests for _sanitize_filename function."""

    def test_removes_invalid_characters(self) -> None:
        assert _sanitize_filename('test<>:"/\\|?*file') == "test_________file"

    def test_strips_leading_trailing_dots_spaces(self) -> None:
        assert _sanitize_filename("  ..test.. ") == "test"

    def test_returns_default_for_empty(self) -> None:
        assert _sanitize_filename("") == "analysis"
        assert _sanitize_filename("...") == "analysis"

    def test_preserves_valid_filename(self) -> None:
        assert _sanitize_filename("my_project-2024") == "my_project-2024"


class TestGenerateFilename:
    """Tests for _generate_filename function."""

    def test_includes_project_name_and_extension(self) -> None:
        filename = _generate_filename("MyProject", "pdf")
        assert filename.startswith("MyProject_")
        assert filename.endswith(".pdf")

    def test_includes_timestamp_format(self) -> None:
        filename = _generate_filename("Test", "txt")
        # Filename format: name_YYYY-MM-DD_HHMMSS.ext
        parts = filename.split("_")
        assert len(parts) >= 3
        # Check date part
        assert len(parts[1]) == 10  # YYYY-MM-DD

    def test_handles_none_project_name(self) -> None:
        filename = _generate_filename(None, "pdf")
        assert filename.startswith("analysis_")

    def test_sanitizes_project_name(self) -> None:
        filename = _generate_filename("My:Project", "pdf")
        assert ":" not in filename


class TestStripMarkdownFormatting:
    """Tests for _strip_markdown_formatting function."""

    def test_removes_headers(self) -> None:
        text = "# Header 1\n## Header 2\n### Header 3"
        result = _strip_markdown_formatting(text)
        assert "Header 1" in result
        assert "#" not in result

    def test_removes_bold_italic(self) -> None:
        text = "This is **bold** and *italic* and __also bold__ and _also italic_"
        result = _strip_markdown_formatting(text)
        assert "bold" in result
        assert "italic" in result
        assert "*" not in result
        assert "_" not in result

    def test_removes_inline_code(self) -> None:
        text = "Use `print()` function"
        result = _strip_markdown_formatting(text)
        assert "print()" in result
        assert "`" not in result

    def test_removes_code_blocks(self) -> None:
        text = "Code:\n```python\nprint('hello')\n```\nEnd"
        result = _strip_markdown_formatting(text)
        assert "print" not in result
        assert "Code:" in result
        # "End" should be present after code block removal
        assert "End" in result

    def test_removes_links_keeps_text(self) -> None:
        text = "Visit [Google](https://google.com) for more"
        result = _strip_markdown_formatting(text)
        assert "Google" in result
        assert "https" not in result
        assert "[" not in result

    def test_collapses_multiple_blank_lines(self) -> None:
        text = "Line 1\n\n\n\n\nLine 2"
        result = _strip_markdown_formatting(text)
        assert "\n\n\n" not in result


class TestExportToTxt:
    """Tests for export_to_txt function."""

    def test_creates_txt_file(self, tmp_path: Path) -> None:
        content = "# Test\n\nThis is **bold** text."
        output = tmp_path / "test.txt"

        result = export_to_txt(content, output)

        assert result == output
        assert output.exists()
        text = output.read_text(encoding="utf-8")
        assert "Test" in text
        assert "bold" in text
        assert "#" not in text
        assert "**" not in text

    def test_handles_empty_content(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.txt"
        result = export_to_txt("", output)

        assert result == output
        assert output.exists()


class TestExportToPdf:
    """Tests for export_to_pdf function."""

    def test_creates_pdf_file(self, tmp_path: Path) -> None:
        content = "# Test Project\n\n## Summary\n\n- Item 1\n- Item 2"
        output = tmp_path / "test.pdf"

        result = export_to_pdf(content, output)

        assert result == output
        assert output.exists()
        # Verify it's a PDF by checking magic bytes
        with open(output, "rb") as f:
            magic = f.read(4)
        assert magic == b"%PDF"

    def test_handles_various_markdown_elements(self, tmp_path: Path) -> None:
        content = """# Main Title

## Section 1

Regular paragraph text.

- Bullet point 1
- Bullet point 2

### Subsection

* Alternative bullet
* Another one

`code snippet`

**Bold text** and *italic text*
"""
        output = tmp_path / "complex.pdf"
        result = export_to_pdf(content, output)

        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_handles_empty_lines(self, tmp_path: Path) -> None:
        content = "Title\n\n\n\nContent"
        output = tmp_path / "spaced.pdf"

        export_to_pdf(content, output)
        assert output.exists()


class TestExportAnalysis:
    """Tests for export_analysis function."""

    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_exports_pdf_when_selected(self, mock_prompt: MagicMock, tmp_path: Path) -> None:
        output_path = tmp_path / "export.pdf"
        mock_prompt.return_value = output_path

        result = export_analysis("# Test", "MyProject", "pdf")

        assert result == output_path
        assert output_path.exists()
        mock_prompt.assert_called_once()

    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_exports_txt_when_selected(self, mock_prompt: MagicMock, tmp_path: Path) -> None:
        output_path = tmp_path / "export.txt"
        mock_prompt.return_value = output_path

        result = export_analysis("# Test", "MyProject", "txt")

        assert result == output_path
        assert output_path.exists()

    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_returns_none_when_cancelled(self, mock_prompt: MagicMock) -> None:
        mock_prompt.return_value = None

        result = export_analysis("# Test", "MyProject", "pdf")

        assert result is None

    def test_returns_none_for_empty_content(self) -> None:
        result = export_analysis("", "MyProject", "pdf")
        assert result is None

        result = export_analysis("   \n\n  ", "MyProject", "pdf")
        assert result is None

    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_adds_extension_if_missing(self, mock_prompt: MagicMock, tmp_path: Path) -> None:
        # User selects file without extension
        output_path = tmp_path / "export"
        mock_prompt.return_value = output_path

        result = export_analysis("# Test", "MyProject", "pdf")

        # Should have .pdf extension added
        assert result is not None
        assert result.suffix == ".pdf"

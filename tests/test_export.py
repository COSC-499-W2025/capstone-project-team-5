"""Tests for the export utility module."""

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
    def test_removes_invalid_characters(self) -> None:
        assert _sanitize_filename('test<>:"/\\|?*file') == "test_________file"

    def test_returns_default_for_empty(self) -> None:
        assert _sanitize_filename("") == "analysis"
        assert _sanitize_filename("...") == "analysis"


class TestGenerateFilename:
    def test_includes_project_name_and_extension(self) -> None:
        filename = _generate_filename("MyProject", "pdf")
        assert filename.startswith("MyProject_") and filename.endswith(".pdf")

    def test_handles_none_project_name(self) -> None:
        assert _generate_filename(None, "pdf").startswith("analysis_")


class TestStripMarkdownFormatting:
    def test_removes_headers_and_formatting(self) -> None:
        text = "# Header\n**bold** and *italic* and `code`"
        result = _strip_markdown_formatting(text)
        assert "Header" in result and "#" not in result
        assert "bold" in result and "**" not in result
        assert "code" in result and "`" not in result

    def test_removes_code_blocks(self) -> None:
        result = _strip_markdown_formatting("Before\n```python\ncode\n```\nAfter")
        assert "code" not in result and "Before" in result and "After" in result

    def test_removes_links_keeps_text(self) -> None:
        result = _strip_markdown_formatting("[Google](https://google.com)")
        assert "Google" in result and "https" not in result


class TestExportToTxt:
    def test_creates_txt_file(self, tmp_path: Path) -> None:
        output = tmp_path / "test.txt"
        result = export_to_txt("# Test\n**bold**", output)
        assert result == output and output.exists()
        text = output.read_text(encoding="utf-8")
        assert "Test" in text and "**" not in text


class TestExportToPdf:
    def test_creates_valid_pdf(self, tmp_path: Path) -> None:
        output = tmp_path / "test.pdf"
        result = export_to_pdf("# Title\n## Section\n- Bullet", output)
        assert result == output and output.exists()
        with open(output, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_handles_complex_markdown(self, tmp_path: Path) -> None:
        content = "# Title\n\n## Section\n\n- Item 1\n* Item 2\n\n**Bold** `code`"
        output = tmp_path / "complex.pdf"
        export_to_pdf(content, output)
        assert output.exists() and output.stat().st_size > 0


class TestExportAnalysis:
    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_exports_pdf(self, mock_prompt: MagicMock, tmp_path: Path) -> None:
        mock_prompt.return_value = tmp_path / "export.pdf"
        result = export_analysis("# Test", "MyProject", "pdf")
        assert result and result.exists()

    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_exports_txt(self, mock_prompt: MagicMock, tmp_path: Path) -> None:
        mock_prompt.return_value = tmp_path / "export.txt"
        result = export_analysis("# Test", "MyProject", "txt")
        assert result and result.exists()

    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_returns_none_when_cancelled(self, mock_prompt: MagicMock) -> None:
        mock_prompt.return_value = None
        assert export_analysis("# Test", "MyProject", "pdf") is None

    def test_returns_none_for_empty_content(self) -> None:
        assert export_analysis("", "MyProject", "pdf") is None
        assert export_analysis("   \n\n  ", "MyProject", "pdf") is None

    @patch("capstone_project_team_5.utils.export.prompt_export_location")
    def test_adds_extension_if_missing(self, mock_prompt: MagicMock, tmp_path: Path) -> None:
        mock_prompt.return_value = tmp_path / "export"
        result = export_analysis("# Test", "MyProject", "pdf")
        assert result and result.suffix == ".pdf"

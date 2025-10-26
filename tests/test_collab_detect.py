import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from docx import Document
from pypdf import PdfWriter

from capstone_project_team_5.collab_detect import CollabDetector


def test_git_repo():
    """Tests root as a git repository using current directory."""

    repo_path = Path(os.getcwd())

    isCollab = CollabDetector.is_collaborative(repo_path)
    numCollaborators = CollabDetector.number_of_collaborators(repo_path)

    assert isCollab is True
    assert numCollaborators == 7


def test_file_ownsherip():
    """Simulates a non-git repo with files owned by different users."""

    # create mock file paths
    fake_file1 = MagicMock()
    fake_file2 = MagicMock()
    fake_file3 = MagicMock()

    # behave as actual files
    fake_file1.is_file.return_value = True
    fake_file2.is_file.return_value = True
    fake_file3.is_file.return_value = True

    # fake stat() results with different user IDs
    fake_file1.stat.return_value = type("Stat", (), {"st_uid": 1000, "st_gid": 100})()
    fake_file2.stat.return_value = type("Stat", (), {"st_uid": 2000, "st_gid": 100})()
    fake_file3.stat.return_value = type("Stat", (), {"st_gid": 200})

    # patch Path.rglob to return these fake files
    with patch.object(Path, "rglob", return_value=[fake_file1, fake_file2, fake_file3]):
        owners = CollabDetector._file_ownership(Path("/fake/path"))

    print("[DEBUG] Simulated file owners:", owners)

    assert owners == {1000, 2000}
    assert len(owners) == 2


def test_document_authors():
    """Using tempfile create mock docx and pdf files for testing document authors."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)

        # create .docx file
        docx_path = tmp_path / "doc1.docx"
        doc = Document()
        doc.add_paragraph("Hello World!")
        doc.core_properties.author = "John"
        doc.core_properties.last_modified_by = "Bob"
        doc.save(docx_path)

        # create .pdf file
        pdf_path = tmp_path / "doc2.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.add_metadata({"/Author": "Charlie"})
        with open(pdf_path, "wb") as f:
            writer.write(f)

        authors = CollabDetector._document_authors(tmp_path)
        numAuthors = CollabDetector.number_of_collaborators(tmp_path)

        assert authors == {"John", "Bob", "Charlie"}
        assert numAuthors == 3

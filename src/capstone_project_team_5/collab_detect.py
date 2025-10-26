import subprocess
from pathlib import Path

from docx import Document
from pypdf import PdfReader


class CollabDetector:
    """
    Detects if a given project is an individual or a collaborative project
    and finds the number of contributors.
    """

    @staticmethod
    def number_of_collaborators(root: Path) -> int:
        """
        Scans a given project directory and returns the number of contributors.

        Args:
            root: Project root directory.

        Returns:
            int: Count of found contributors.
        """

        # sequential fallback for each method

        authors = CollabDetector._git_authors(root)

        if len(authors) > 1:
            return len(authors)

        authors = CollabDetector._file_ownership(root)

        if len(authors) > 1:
            return len(authors)

        authors = CollabDetector._document_authors(root)

        if len(authors) > 1:
            return len(authors)

        return 1

    @staticmethod
    def is_collaborative(root: Path) -> bool:
        """
        Uses multiple methods to distinguish if a project
        appears to be a collaborative project or not.

        Args:
            root: Project root directory.

        Returns:
            boolean: Returns True if the project appears to be collaborative else False.
        """
        return CollabDetector.number_of_collaborators(root) > 1

    @staticmethod
    def _is_git_repository(root: Path) -> bool:
        """Helper function for _git_authors"""
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return result.returncode == 0
        except (OSError, ValueError):
            return False

    @staticmethod
    def _git_authors(root: Path) -> set[str]:
        """
        Returns the set of authors working on a project if root is a git repository.

        Args:
            root: Project root directory.

        Returns:
            set[str]: Returns set of author names.
        """

        ignore_list = {"github-classroom[bot]", "dependabot[bot]", "GitHub"}
        authors: set[str] = set()

        # check if root is a repo
        if not CollabDetector._is_git_repository(root):
            return authors

        try:
            result = subprocess.run(
                ["git", "shortlog", "-sne", "--all"],
                cwd=str(root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )

            output = result.stdout.strip()

            for line in output.splitlines():
                if not line.strip():
                    continue
                parts = line.strip().split("\t")
                if len(parts) < 2:
                    continue
                author_info = parts[1]

                if "<" in author_info and ">" in author_info:
                    email = author_info[author_info.index("<") + 1 : author_info.index(">")].strip()
                    if email not in ignore_list:
                        authors.add(email)
                else:
                    name = author_info.strip()
                    if name not in ignore_list:
                        authors.add(name)

        except subprocess.CalledProcessError:
            return authors

        return authors

    @staticmethod
    def _file_ownership(root: Path) -> set[int]:
        """
        Scans all files under the root directory and returns a set of unique ID's
        representing ownership.

        Args:
            root: Project root directory.

        Returns:
            set[int]: Sets of unique ID's representing ownership contributions.
        """

        uids: set[int] = set()
        gids: set[int] = set()

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                stat_info = file_path.stat()
                uids.add(stat_info.st_uid)
                gids.add(stat_info.st_gid)

            except Exception:
                continue

        # return user ids if there are multiple over group ids for more reliability
        if len(uids) > 1:
            return uids
        elif len(gids) > 1:
            return gids
        else:
            # return whatever single user id we have
            return uids or gids

    def _document_authors(root: Path) -> set[str]:
        """
        Scans document files (.docx, .pdf) under the root folder
        and returns a set of unique authors found in the file metadata.
        """

        authors: set[str] = set()
        ignore_list = {"Unknown", None, "python-docx"}

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                if file_path.suffix.lower() == ".docx":
                    doc: Document = Document(file_path)
                    properties = doc.core_properties

                    if properties and properties.author not in ignore_list:
                        authors.add(properties.author.strip())

                    # check last modified by as well
                    if (
                        properties.last_modified_by
                        and properties.last_modified_by not in ignore_list
                    ):
                        authors.add(properties.last_modified_by.strip())

                elif file_path.suffix.lower() == ".pdf":
                    reader = PdfReader(file_path)
                    info = reader.metadata
                    if info and info.author and info.author not in ignore_list:
                        authors.add(info.author.strip())
            except Exception:
                # ignore unreadable files
                continue
        return authors

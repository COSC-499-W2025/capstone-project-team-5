from pathlib import Path

from docx import Document
from pypdf import PdfReader

from capstone_project_team_5.utils.git_helper import is_git_repo, run_git_command


class CollabDetector:
    """
    Detects if a given project is an individual or a collaborative project
    and finds the number of contributors.
    """

    @staticmethod
    def collaborator_summary(root: Path) -> tuple[int, set[str]]:
        """
        Returns a summary of collaboration for the given project.
        Returns the number of collaborators found and their identities
        if possbile.

        Args:
            root: Project root directory.

        Returns:
            tuple: Number of collaborators and their identities.
        """

        if is_git_repo(root=root):
            git_authors = CollabDetector._git_authors(root=root)
            return len(git_authors), git_authors

        doc_authors = CollabDetector._document_authors(root=root)
        if doc_authors:
            return len(doc_authors), doc_authors

        ownership_ids = CollabDetector._file_ownership(root=root)
        if ownership_ids:
            str_uids = {str(uid) for uid in ownership_ids}
            return len(str_uids), str_uids

        return 1, {"Unknown"}

    @staticmethod
    def format_collaborators(summary: tuple[int, set[str]]) -> str:
        """
        Returns a nicely formatted string for CLI display.

        Args:
            summary: Tuple (num_collaborators, identities).

        Returns:
            str: Human-readable formatted summary.
        """

        num, identities = summary

        if not identities:
            return "👤 No collaborators detected."

        names = sorted(identities)

        if len(names) == 1 and ("Unknown" in names or names[0].isdigit()):
            return "👤 Single contributor (identity unknown)."

        names_list = ", ".join(names)
        plural = "collaborator" if num == 1 else "collaborators"

        return f"👥 {num} {plural} detected: {names_list}"

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
        if not is_git_repo(root=root):
            return authors

        try:
            git_command = "shortlog -sc --all"
            result = run_git_command(command=git_command, root=root)

            if result == "":
                return authors

            output = result.strip()

            for line in output.splitlines():
                if not line.strip():
                    continue

                parts = line.strip().split("\t")

                if len(parts) == 2:
                    name = parts[1].strip()
                else:
                    # if we cant split on a tab
                    tokens = line.strip().split(maxsplit=1)
                    if len(tokens) != 2:
                        continue
                    name = tokens[1].strip()

                if name in ignore_list:
                    continue

                authors.add(name)

        except Exception:
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

    @staticmethod
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

from __future__ import annotations

from capstone_project_team_5.services.git_ingest_local import (
    parse_numstat,
    parse_review_trailers,
)


def test_parse_numstat_skips_binary_and_parses_numeric() -> None:
    out = """10	2	src/app.py
-	-	assets/logo.png
3	0	src/util/helpers.py
"""
    files = parse_numstat(out)
    paths = [f.path for f in files]
    assert paths == ["src/app.py", "src/util/helpers.py"]
    assert files[0].added == 10 and files[0].deleted == 2


def test_parse_review_trailers_variants() -> None:
    msg = """
    Merge pull request #42 from feature/thing

    Add awesome feature

    Reviewed-by: Jane Doe <jane@example.com>
    reviewed-by: john@example.com
    Co-authored-by: Someone Else <co@example.com>
    """
    reviewers = parse_review_trailers(msg)
    assert "Jane Doe <jane@example.com>" in reviewers
    assert "john@example.com" in reviewers

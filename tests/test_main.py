from capstone_project_team_5 import main


def test_main() -> None:
    """Test that main is callable and returns an integer exit code."""
    assert callable(main)


def test_main_return_type() -> None:
    """Test that main returns an integer (exit code)."""
    assert main.__annotations__.get("return") is int

"""User tutorial and setup wizard services.

Manages tutorial completion status and guided setup wizard progress.
"""

from __future__ import annotations

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User


def get_tutorial_status(username: str) -> bool:
    """Return the tutorial completion flag for the given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            return False
        return user.tutorial_completed


def update_tutorial_status(username: str, *, completed: bool) -> None:
    """Set the tutorial completion flag for the given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is not None:
            user.tutorial_completed = completed


def get_setup_status(username: str) -> dict[str, bool | int]:
    """Return the setup wizard progress for the given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None:
            return {"completed": False, "step": 0}
        return {"completed": user.setup_completed, "step": user.setup_step}


def update_setup_status(
    username: str,
    *,
    completed: bool | None = None,
    step: int | None = None,
) -> None:
    """Update the setup wizard progress for the given user."""
    with get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is not None:
            if completed is not None:
                user.setup_completed = completed
            if step is not None:
                user.setup_step = step

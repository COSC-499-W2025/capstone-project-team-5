"""Shared dependencies for API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, status


def get_current_username(
    x_username: Annotated[
        str | None,
        Header(
            description=(
                "Current username. In production, this should be extracted "
                "from authenticated session/JWT token."
            )
        ),
    ] = None,
) -> str:
    """Get the current username from request context.

    NOTE: This is a simplified implementation using a header.
    In production, this should extract from JWT/session.

    Args:
        x_username: Username from X-Username header (temporary mechanism).

    Returns:
        str: Authenticated username.

    Raises:
        HTTPException: If authentication is missing (401).
    """
    if not x_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Please provide X-Username header.",
        )
    return x_username


def get_optional_username(
    x_username: Annotated[
        str | None,
        Header(
            description=(
                "Current username. In production, this should be extracted "
                "from authenticated session/JWT token."
            )
        ),
    ] = None,
) -> str | None:
    """Get the current username if provided, or None for anonymous access.

    Unlike ``get_current_username`` this does **not** raise 401 when the
    header is missing.  Use this for endpoints that support both
    authenticated and anonymous callers (e.g. consent).

    Args:
        x_username: Username from X-Username header (temporary mechanism).

    Returns:
        str | None: Authenticated username, or None for anonymous access.
    """
    return x_username or None

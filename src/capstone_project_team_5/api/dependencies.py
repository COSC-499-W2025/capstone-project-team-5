"""Shared dependencies for API routes."""

from __future__ import annotations

import jwt
from fastapi import HTTPException, Request, status

from capstone_project_team_5.services.jwt_service import decode_access_token


def _extract_bearer_token(request: Request) -> str | None:
    """Pull the raw token string out of the Authorization header, or return None."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.removeprefix("Bearer ").strip()
    return token or None


def get_current_username(request: Request) -> str:
    """Get the current username from a verified JWT Bearer token.

    Reads the ``Authorization: Bearer <token>`` header, verifies the
    signature and expiry, and returns the ``sub`` claim (username).

    Returns:
        str: Authenticated username.

    Raises:
        HTTPException 401: Token is missing, expired, or invalid.
    """
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication. Please provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    username: str | None = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )
    return username


def get_optional_username(request: Request) -> str | None:
    """Get the current username if a valid token is provided, else None.

    Unlike ``get_current_username`` this does **not** raise 401 when the
    token is absent.  Use this for endpoints that support both authenticated
    and anonymous callers (e.g. consent).

    Returns:
        str | None: Authenticated username, or None for anonymous access.
    """
    token = _extract_bearer_token(request)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        return payload.get("sub") or None
    except jwt.InvalidTokenError:
        return None

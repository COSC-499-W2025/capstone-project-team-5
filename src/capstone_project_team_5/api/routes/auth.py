"""Authentication routes — login and registration.

These endpoints wrap the existing ``services.auth`` helpers so the
Electron front-end can authenticate without needing a direct DB connection.

Endpoints
---------
POST /api/auth/register  — create a new account
POST /api/auth/login     — verify credentials for an existing account

Both endpoints return ``{"username": "<username>", "token": "<jwt>"}`` on
success.  The front-end must include the token on subsequent requests as:
    Authorization: Bearer <token>
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from capstone_project_team_5.services.auth import authenticate_user, create_user
from capstone_project_team_5.services.jwt_service import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / response schemas ────────────────────────────────────────────


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    username: str
    token: str


# ── Routes ─────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
def register(body: AuthRequest) -> AuthResponse:
    """Register a new user with a username and password.

    Args:
        body: ``username`` and ``password`` fields.

    Returns:
        AuthResponse: The created username and a signed JWT access token.

    Raises:
        HTTPException 400: Username already exists or invalid input.
    """
    ok, error = create_user(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    username = body.username.strip()
    return AuthResponse(username=username, token=create_access_token(username))


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate an existing user",
)
def login(body: AuthRequest) -> AuthResponse:
    """Log in with an existing username and password.

    Args:
        body: ``username`` and ``password`` fields.

    Returns:
        AuthResponse: The authenticated username and a signed JWT access token.

    Raises:
        HTTPException 401: Invalid credentials.
    """
    ok, error = authenticate_user(body.username, body.password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Invalid username or password.",
        )
    username = body.username.strip()
    return AuthResponse(username=username, token=create_access_token(username))

"""Authentication helpers for the TUI.

This module provides a minimal username/password authentication layer
backed by the users table. Passwords are stored as salted PBKDF2 hashes.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from capstone_project_team_5.data.db import get_session
from capstone_project_team_5.data.models import User

_PBKDF2_ITERATIONS = 100_000
_SALT_BYTES = 16


def _hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash for the given password.

    The result is stored as ``<salt_hex>:<hash_hex>``.
    """
    salt = os.urandom(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{derived.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored ``salt:hash`` string."""
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)
    except ValueError:
        return False

    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except ValueError:
        return False

    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(candidate, expected)


def create_user(username: str, password: str) -> tuple[bool, str | None]:
    """Create a new user account.

    Returns:
        Tuple of (success flag, error message). On success, error is None.
    """
    username_clean = username.strip()
    if not username_clean:
        return False, "Username cannot be empty."
    if not password:
        return False, "Password cannot be empty."

    try:
        with get_session() as session:
            existing = session.query(User).filter(User.username == username_clean).first()
            if existing is not None:
                return False, "Username already exists."

            user = User(username=username_clean, password_hash=_hash_password(password))
            session.add(user)
        return True, None
    except Exception as exc:
        return False, f"Failed to create user: {exc}"


def authenticate_user(username: str, password: str) -> tuple[bool, str | None]:
    """Authenticate a user by username and password.

    Returns:
        Tuple of (success flag, error message). On success, error is None.
    """
    username_clean = username.strip()
    if not username_clean or not password:
        return False, "Username and password are required."

    try:
        with get_session() as session:
            user = session.query(User).filter(User.username == username_clean).first()
            if user is None:
                return False, "Invalid username or password."

            if not _verify_password(password, user.password_hash):
                return False, "Invalid username or password."
    except Exception as exc:
        return False, f"Authentication failed: {exc}"

    return True, None

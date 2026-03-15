"""JWT token creation and verification.

The secret key is read from the JWT_SECRET_KEY environment variable.
If not set, a random key is generated for the current process lifetime —
meaning all tokens are invalidated on server restart.  Set JWT_SECRET_KEY
in your .env file to persist sessions across restarts.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta

import jwt

# Secret used to sign tokens.  Regenerated each process start when not set.
_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY") or secrets.token_hex(32)
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 7


def create_access_token(username: str) -> str:
    """Return a signed JWT encoding the given username.

    The token expires after ``_TOKEN_EXPIRE_DAYS`` days.
    """
    now = datetime.now(datetime.UTC)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(days=_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT.

    Returns the payload dict on success.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is malformed or signature is invalid.
    """
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])

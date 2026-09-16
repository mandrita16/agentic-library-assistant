"""
auth/security.py

Handles:
1. Password hashing and verification
2. JWT access-token creation and verification

Other parts of the application should use these functions instead
of directly calling bcrypt or jose.
"""

from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
)


# Password hashing configuration
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password.

    The original password should never be stored in the database.
    """

    return _pwd_context.hash(plain_password)


def verify_password(
    plain_password: str,
    password_hash: str
) -> bool:
    """
    Check whether a plain-text password matches the stored hash.
    """

    return _pwd_context.verify(
        plain_password,
        password_hash
    )


def create_access_token(
    subject: str,
    role: str
) -> str:
    """
    Create a JWT access token.

    subject:
        Student ID or Admin ID.

    role:
        "student" or "admin".
    """

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return token


def decode_access_token(
    token: str
) -> dict | None:
    """
    Decode and validate a JWT.

    Returns:
        Payload dictionary if valid.

    Returns:
        None if the token is invalid or expired.
    """

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        return payload

    except JWTError:
        return None
"""
app/auth/dependencies.py
------------------------
Authentication dependencies for protected API endpoints.

JWT tokens are sent using:

Authorization: Bearer <access_token>
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.auth.security import decode_access_token


# ============================================================
# BEARER AUTHENTICATION
# ============================================================

bearer_scheme = HTTPBearer(
    auto_error=False
)


# ============================================================
# ROLE CHECKING
# ============================================================

def _require_role(
    credentials: HTTPAuthorizationCredentials | None,
    expected_role: str,
) -> str:

    # --------------------------------------------------------
    # No token provided
    # --------------------------------------------------------

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please provide a Bearer token.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # --------------------------------------------------------
    # Extract JWT
    # --------------------------------------------------------

    token = credentials.credentials

    # --------------------------------------------------------
    # Decode JWT
    # --------------------------------------------------------

    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # --------------------------------------------------------
    # Check role
    # --------------------------------------------------------

    role = payload.get("role")

    if role != expected_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This endpoint requires a {expected_role} account.",
        )

    # --------------------------------------------------------
    # Get user identity
    # --------------------------------------------------------

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: user identity is missing.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return user_id


# ============================================================
# STUDENT AUTHENTICATION
# ============================================================

def get_current_student(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> str:

    return _require_role(
        credentials,
        "student",
    )


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> str:

    return _require_role(
        credentials,
        "admin",
    )
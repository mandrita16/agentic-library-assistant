"""
auth/dependencies.py
----------------------
FastAPI "Depends()" functions that every protected route uses instead of
trusting a student_id/admin_id the client sends in the request body.
The token is the only source of truth for who's making the request —
this is what stops a student from issuing "issue_book" as someone else
just by changing a field in the JSON body.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.auth.security import decode_access_token

# tokenUrl is just what shows in the /docs "Authorize" button — the real
# login endpoint is POST /auth/login (this doesn't have to match exactly
# for a JSON-body login flow, but it's kept aligned for clarity).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def _require_role(token: str | None, expected_role: str) -> str:
    if token is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated. Include an Authorization: Bearer <token> header.")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token. Please log in again.")
    if payload.get("role") != expected_role:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"This endpoint requires a {expected_role} account.")
    return payload["sub"]


def get_current_student(token: str = Depends(oauth2_scheme)) -> str:
    """Returns the authenticated student_id, or raises 401/403. Use as: student_id: str = Depends(get_current_student)"""
    return _require_role(token, "student")


def get_current_admin(token: str = Depends(oauth2_scheme)) -> str:
    """Returns the authenticated admin_id, or raises 401/403."""
    return _require_role(token, "admin")

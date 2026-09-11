"""
auth/security.py
------------------
Two independent concerns, kept in one small file since neither is more
than a few lines: password hashing (bcrypt via passlib) and JWT
issuing/verification (python-jose). Nothing else in the app should call
bcrypt or jose directly — always go through these functions, so there's
exactly one place that knows the hashing scheme and token format.
"""

from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, role: str) -> str:
    """
    subject: the student_id or admin_id this token is for.
    role: "student" or "admin" — checked by the dependencies in
    auth/dependencies.py to enforce who can call which endpoint.
    """
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Returns the payload dict ({"sub": ..., "role": ...}) if the token is valid and unexpired, else None."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None

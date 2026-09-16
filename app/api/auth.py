"""
api/auth.py
-----------
Authentication API endpoints.

Provides:
    POST /auth/register
    POST /auth/login
    POST /auth/admin/register
    POST /auth/admin/login

The endpoints accept JSON request bodies.
Authentication logic is handled by auth_service.py.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.services import auth_service


router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# ============================================================
# REQUEST MODELS
# ============================================================

class StudentRegisterRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class AdminRegisterRequest(BaseModel):
    admin_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)
    setup_key: str = Field(..., min_length=1)


class AdminLoginRequest(BaseModel):
    admin_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


# ============================================================
# STUDENT AUTHENTICATION
# ============================================================

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
def register(req: StudentRegisterRequest):
    """
    Register a new student account.
    """

    return auth_service.register_student(
        student_id=req.student_id,
        name=req.name,
        department=req.department,
        password=req.password
    )


@router.post("/login")
def login(req: LoginRequest):
    """
    Login an existing student and receive a JWT access token.
    """

    return auth_service.login_student(
        student_id=req.student_id,
        password=req.password
    )


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

@router.post(
    "/admin/register",
    status_code=status.HTTP_201_CREATED
)
def admin_register(req: AdminRegisterRequest):
    """
    Register a new admin account.

    Requires the ADMIN_SETUP_KEY configured in .env.
    """

    return auth_service.register_admin(
        admin_id=req.admin_id,
        name=req.name,
        password=req.password,
        setup_key=req.setup_key
    )


@router.post("/admin/login")
def admin_login(req: AdminLoginRequest):
    """
    Login an existing admin and receive a JWT access token.
    """

    return auth_service.login_admin(
        admin_id=req.admin_id,
        password=req.password
    )
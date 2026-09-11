"""
api/auth.py
------------
All four auth endpoints. Deliberately simple JSON bodies (not OAuth2's
form-data spec) so the frontend can just fetch() with JSON like every
other endpoint in this API — the OAuth2PasswordBearer scheme used in
auth/dependencies.py only cares about the Authorization header on
protected routes, not how /login itself receives credentials.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class StudentRegisterRequest(BaseModel):
    student_id: str
    name: str
    department: str
    password: str


class LoginRequest(BaseModel):
    student_id: str
    password: str


class AdminRegisterRequest(BaseModel):
    admin_id: str
    name: str
    password: str
    setup_key: str


class AdminLoginRequest(BaseModel):
    admin_id: str
    password: str


@router.post("/register")
def register(req: StudentRegisterRequest):
    return auth_service.register_student(req.student_id, req.name, req.department, req.password)


@router.post("/login")
def login(req: LoginRequest):
    return auth_service.login_student(req.student_id, req.password)


@router.post("/admin/register")
def admin_register(req: AdminRegisterRequest):
    """Requires ADMIN_SETUP_KEY from .env as setup_key \u2014 prevents open self-registration as admin."""
    return auth_service.register_admin(req.admin_id, req.name, req.password, req.setup_key)


@router.post("/admin/login")
def admin_login(req: AdminLoginRequest):
    return auth_service.login_admin(req.admin_id, req.password)

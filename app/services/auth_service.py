"""
services/auth_service.py
------------------------
Registration and login logic.

This file handles the application-level authentication rules:
- duplicate student/admin IDs
- password verification
- admin setup-key verification
- JWT creation

Password hashing and JWT implementation itself lives in auth/security.py.
"""

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.database.mongo import (
    students_collection,
    admins_collection,
)

from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
)

from app.config import ADMIN_SETUP_KEY


# ============================================================
# STUDENT REGISTRATION
# ============================================================

def register_student(
    student_id: str,
    name: str,
    department: str,
    password: str,
) -> dict:

    student_id = student_id.strip()
    name = name.strip()
    department = department.strip()

    if not student_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="student_id is required.",
        )

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required.",
        )

    if not department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="department is required.",
        )

    # Check whether student already exists
    existing_student = students_collection.find_one(
        {"student_id": student_id}
    )

    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this student_id already exists.",
        )

    # Hash password before storing it
    password_hash = hash_password(password)

    # Create student document
    try:
        students_collection.insert_one({
            "student_id": student_id,
            "name": name,
            "department": department,
            "password_hash": password_hash,
            "outstanding_fine": 0.0,
        })
    except DuplicateKeyError:
        # Protect against two registration requests arriving
        # at the same time.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this student_id already exists.",
        )

    return {
        "success": True,
        "message": "Registered. You can now log in.",
    }


# ============================================================
# STUDENT LOGIN
# ============================================================

def login_student(
    student_id: str,
    password: str,
) -> dict:

    student_id = student_id.strip()

    # Find student
    student = students_collection.find_one(
        {"student_id": student_id}
    )

    # Student doesn't exist
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect student_id or password.",
        )

    password_hash = student.get("password_hash")

    # Password hash missing
    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect student_id or password.",
        )

    # Verify password
    if not verify_password(password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect student_id or password.",
        )

    # Create JWT
    token = create_access_token(
        subject=student_id,
        role="student",
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "student_id": student_id,
        "name": student.get("name"),
    }


# ============================================================
# ADMIN REGISTRATION
# ============================================================

def register_admin(
    admin_id: str,
    name: str,
    password: str,
    setup_key: str,
) -> dict:

    admin_id = admin_id.strip()
    name = name.strip()

    # Verify admin setup key
    if setup_key != ADMIN_SETUP_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid setup key. Admin registration is restricted.",
        )

    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin_id is required.",
        )

    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name is required.",
        )

    # Check whether admin already exists
    existing_admin = admins_collection.find_one(
        {"admin_id": admin_id}
    )

    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin with this admin_id already exists.",
        )

    # Hash password
    password_hash = hash_password(password)

    # Create admin document
    try:
        admins_collection.insert_one({
            "admin_id": admin_id,
            "name": name,
            "password_hash": password_hash,
        })
    except DuplicateKeyError:
        # Protect against concurrent duplicate registration.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin with this admin_id already exists.",
        )

    return {
        "success": True,
        "message": "Admin registered. You can now log in.",
    }


# ============================================================
# ADMIN LOGIN
# ============================================================

def login_admin(
    admin_id: str,
    password: str,
) -> dict:

    admin_id = admin_id.strip()

    # Find admin
    admin = admins_collection.find_one(
        {"admin_id": admin_id}
    )

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin_id or password.",
        )

    password_hash = admin.get("password_hash")

    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin_id or password.",
        )

    # Verify password
    if not verify_password(password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin_id or password.",
        )

    # Create JWT
    token = create_access_token(
        subject=admin_id,
        role="admin",
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "admin_id": admin_id,
        "name": admin.get("name"),
    }

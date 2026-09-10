"""
services/auth_service.py
--------------------------
Registration and login logic. Kept separate from auth/security.py:
that file knows HOW to hash/verify/sign; this file knows the actual
student/admin registration rules (duplicate IDs, wrong passwords, etc).
"""

from app.database.mongo import students_collection, admins_collection
from app.auth.security import hash_password, verify_password, create_access_token


def register_student(student_id: str, name: str, department: str, password: str) -> dict:
    if students_collection.find_one({"student_id": student_id}):
        return {"success": False, "message": "A student with this student_id already exists."}
    students_collection.insert_one({
        "student_id": student_id,
        "name": name,
        "department": department,
        "password_hash": hash_password(password),
        "outstanding_fine": 0.0,
    })
    return {"success": True, "message": "Registered. You can now log in."}


def login_student(student_id: str, password: str) -> dict:
    student = students_collection.find_one({"student_id": student_id})
    if not student or "password_hash" not in student or not verify_password(password, student["password_hash"]):
        return {"success": False, "message": "Incorrect student_id or password."}
    token = create_access_token(subject=student_id, role="student")
    return {"success": True, "access_token": token, "token_type": "bearer", "student_id": student_id, "name": student.get("name")}


def register_admin(admin_id: str, name: str, password: str, setup_key: str) -> dict:
    from app.config import ADMIN_SETUP_KEY
    if setup_key != ADMIN_SETUP_KEY:
        return {"success": False, "message": "Invalid setup key \u2014 admin accounts can't be self-registered without it."}
    if admins_collection.find_one({"admin_id": admin_id}):
        return {"success": False, "message": "An admin with this admin_id already exists."}
    admins_collection.insert_one({
        "admin_id": admin_id,
        "name": name,
        "password_hash": hash_password(password),
    })
    return {"success": True, "message": "Admin registered. You can now log in."}


def login_admin(admin_id: str, password: str) -> dict:
    admin = admins_collection.find_one({"admin_id": admin_id})
    if not admin or not verify_password(password, admin["password_hash"]):
        return {"success": False, "message": "Incorrect admin_id or password."}
    token = create_access_token(subject=admin_id, role="admin")
    return {"success": True, "access_token": token, "token_type": "bearer", "admin_id": admin_id, "name": admin.get("name")}

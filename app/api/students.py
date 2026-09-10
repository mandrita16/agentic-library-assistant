"""
api/students.py
----------------
Student-facing account endpoints (non-chat).
"""

from fastapi import APIRouter
from app.services import student_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/{student_id}/dashboard")
def dashboard(student_id: str):
    """Returns: books_borrowed, borrowed_details, due_soon, active_reservations, outstanding_fine."""
    return student_service.get_dashboard(student_id)

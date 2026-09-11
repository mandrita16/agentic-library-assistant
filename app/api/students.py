"""
api/students.py
---------------
Student-facing account endpoints.
"""

from fastapi import APIRouter, HTTPException

from app.services import student_service


router = APIRouter(
    prefix="/students",
    tags=["students"]
)


@router.get("/{student_id}/dashboard")
def get_student_dashboard(student_id: str):
    """
    Return the student's library dashboard.

    Includes:
    - borrowed books
    - due/overdue information
    - active reservations
    - outstanding fine
    """

    if not student_id.strip():
        raise HTTPException(
            status_code=400,
            detail="student_id cannot be empty."
        )

    return student_service.get_dashboard(student_id)
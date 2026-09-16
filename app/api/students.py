"""
api/students.py
---------------
Student-facing account endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_student
from app.services import student_service


router = APIRouter(
    prefix="/students",
    tags=["students"]
)


@router.get("/{student_id}/dashboard")
def get_student_dashboard(
    student_id: str,
    current_student_id: str = Depends(get_current_student),
):
    """
    Return the authenticated student's library dashboard.

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

    # Prevent one student from viewing another student's account.
    if student_id != current_student_id:
        raise HTTPException(
            status_code=403,
            detail="You can only access your own student dashboard."
        )

    return student_service.get_dashboard(
        current_student_id
    )
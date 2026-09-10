"""
api/students.py
----------------
The path takes student_id for readability in the URL, but the actual
authorization check ignores it in favor of the token — a student can
only ever fetch their OWN dashboard. (An admin-facing "view any
student's dashboard" endpoint would be a reasonable addition to
api/admin.py later, but isn't in scope here.)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.services import student_service
from app.auth.dependencies import get_current_student

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/{student_id}/dashboard")
def dashboard(student_id: str, current_student_id: str = Depends(get_current_student)):
    if student_id != current_student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own dashboard.")
    return student_service.get_dashboard(student_id)

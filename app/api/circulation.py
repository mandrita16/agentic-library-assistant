"""
api/circulation.py
------------------
Direct circulation endpoints for issuing, returning,
renewing and reserving books.

All circulation operations are restricted to the
authenticated student.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_student
from app.services import circulation_service


router = APIRouter(
    prefix="/circulation",
    tags=["circulation"]
)


# ================================================================
# REQUEST MODEL
# ================================================================

class CirculationRequest(BaseModel):
    """
    Common request body for circulation operations.
    """

    book_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique ID of the book"
    )

    student_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique ID of the student"
    )


# ================================================================
# RESULT HANDLER
# ================================================================

def handle_result(result: dict):
    """
    Convert service failures into HTTP responses.
    """

    if not result.get("success", False):
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "message",
                "Circulation operation failed."
            )
        )

    return result


# ================================================================
# STUDENT ID VALIDATION
# ================================================================

def validate_student(
    request_student_id: str,
    authenticated_student_id: str
):
    """
    Make sure the student ID in the request matches
    the student authenticated through the JWT.
    """

    if request_student_id != authenticated_student_id:
        raise HTTPException(
            status_code=403,
            detail="You can only perform circulation operations for your own account."
        )


# ================================================================
# ISSUE BOOK
# ================================================================

@router.post("/issue")
def issue_book(
    req: CirculationRequest,
    current_student_id: str = Depends(get_current_student)
):
    """Issue a book to the authenticated student."""

    validate_student(
        req.student_id,
        current_student_id
    )

    result = circulation_service.issue_book(
        req.book_id,
        current_student_id
    )

    return handle_result(result)


# ================================================================
# RETURN BOOK
# ================================================================

@router.post("/return")
def return_book(
    req: CirculationRequest,
    current_student_id: str = Depends(get_current_student)
):
    """Return a borrowed book for the authenticated student."""

    validate_student(
        req.student_id,
        current_student_id
    )

    result = circulation_service.return_book(
        req.book_id,
        current_student_id
    )

    return handle_result(result)


# ================================================================
# RENEW BOOK
# ================================================================

@router.post("/renew")
def renew_book(
    req: CirculationRequest,
    current_student_id: str = Depends(get_current_student)
):
    """Renew a borrowed book for the authenticated student."""

    validate_student(
        req.student_id,
        current_student_id
    )

    result = circulation_service.renew_book(
        req.book_id,
        current_student_id
    )

    return handle_result(result)


# ================================================================
# RESERVE BOOK
# ================================================================

@router.post("/reserve")
def reserve_book(
    req: CirculationRequest,
    current_student_id: str = Depends(get_current_student)
):
    """Reserve a book for the authenticated student."""

    validate_student(
        req.student_id,
        current_student_id
    )

    result = circulation_service.reserve_book(
        req.book_id,
        current_student_id
    )

    return handle_result(result)


# ================================================================
# CANCEL RESERVATION
# ================================================================

@router.post("/cancel-reservation")
def cancel_reservation(
    req: CirculationRequest,
    current_student_id: str = Depends(get_current_student)
):
    """Cancel a reservation for the authenticated student."""

    validate_student(
        req.student_id,
        current_student_id
    )

    result = circulation_service.cancel_reservation(
        req.book_id,
        current_student_id
    )

    return handle_result(result)
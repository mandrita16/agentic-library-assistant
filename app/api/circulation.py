"""
api/circulation.py
------------------
Direct circulation endpoints for issuing, returning,
renewing and reserving books.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import circulation_service


router = APIRouter(
    prefix="/circulation",
    tags=["circulation"]
)


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


@router.post("/issue")
def issue_book(req: CirculationRequest):
    """Issue a book to a student."""

    result = circulation_service.issue_book(
        req.book_id,
        req.student_id
    )

    return handle_result(result)


@router.post("/return")
def return_book(req: CirculationRequest):
    """Return a borrowed book."""

    result = circulation_service.return_book(
        req.book_id,
        req.student_id
    )

    return handle_result(result)


@router.post("/renew")
def renew_book(req: CirculationRequest):
    """Renew a borrowed book."""

    result = circulation_service.renew_book(
        req.book_id,
        req.student_id
    )

    return handle_result(result)


@router.post("/reserve")
def reserve_book(req: CirculationRequest):
    """Reserve a book that is currently unavailable."""

    result = circulation_service.reserve_book(
        req.book_id,
        req.student_id
    )

    return handle_result(result)


@router.post("/cancel-reservation")
def cancel_reservation(req: CirculationRequest):
    """Cancel an active book reservation."""

    result = circulation_service.cancel_reservation(
        req.book_id,
        req.student_id
    )

    return handle_result(result)
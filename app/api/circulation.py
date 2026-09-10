"""
api/circulation.py
--------------------
Direct circulation endpoints — a librarian-facing desk UI or a student
app's "My Books" screen would call these directly rather than going
through the chat agent.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services import circulation_service

router = APIRouter(prefix="/circulation", tags=["circulation"])


class CirculationRequest(BaseModel):
    book_id: str
    student_id: str


@router.post("/issue")
def issue(req: CirculationRequest):
    return circulation_service.issue_book(req.book_id, req.student_id)


@router.post("/return")
def return_book(req: CirculationRequest):
    return circulation_service.return_book(req.book_id, req.student_id)


@router.post("/renew")
def renew(req: CirculationRequest):
    return circulation_service.renew_book(req.book_id, req.student_id)


@router.post("/reserve")
def reserve(req: CirculationRequest):
    return circulation_service.reserve_book(req.book_id, req.student_id)


@router.post("/cancel-reservation")
def cancel_reservation(req: CirculationRequest):
    return circulation_service.cancel_reservation(req.book_id, req.student_id)

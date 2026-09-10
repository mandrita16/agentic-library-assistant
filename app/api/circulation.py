"""
api/circulation.py
--------------------
student_id is no longer part of the request body — it's taken from the
authenticated token. Without this, any logged-in student could pass a
different student_id in the JSON body and issue/return/renew books on
someone else's account. book_id is still supplied by the client since
there's no ambiguity about which book a request is about.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services import circulation_service
from app.auth.dependencies import get_current_student

router = APIRouter(prefix="/circulation", tags=["circulation"])


class BookIdRequest(BaseModel):
    book_id: str


@router.post("/issue")
def issue(req: BookIdRequest, student_id: str = Depends(get_current_student)):
    return circulation_service.issue_book(req.book_id, student_id)


@router.post("/return")
def return_book(req: BookIdRequest, student_id: str = Depends(get_current_student)):
    return circulation_service.return_book(req.book_id, student_id)


@router.post("/renew")
def renew(req: BookIdRequest, student_id: str = Depends(get_current_student)):
    return circulation_service.renew_book(req.book_id, student_id)


@router.post("/reserve")
def reserve(req: BookIdRequest, student_id: str = Depends(get_current_student)):
    return circulation_service.reserve_book(req.book_id, student_id)


@router.post("/cancel-reservation")
def cancel_reservation(req: BookIdRequest, student_id: str = Depends(get_current_student)):
    return circulation_service.cancel_reservation(req.book_id, student_id)

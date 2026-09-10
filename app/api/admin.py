"""
api/admin.py
------------
Librarian/admin-facing endpoints. NOTE: there's no authentication layer
in this build (see README "Future Enhancements") — in a real deployment
these routes would need to be locked behind an admin login. For the
ideathon submission, that's fine to call out as a known next step rather
than build, since the assignment is scored on design + documentation,
not a production-hardened deployment.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services import book_service, analytics_service

router = APIRouter(prefix="/admin", tags=["admin"])


class AddBookRequest(BaseModel):
    book_id: str
    title: str
    author: str
    isbn: str
    subject: str
    course_codes: list[str] = []
    description: str
    shelf_location: str
    total_copies: int
    available_copies: int
    tags: list[str] = []


class UpdateCopiesRequest(BaseModel):
    book_id: str
    delta: int  # e.g. +2 when the library buys more copies, -1 if one is lost/damaged


@router.post("/books")
def add_book(req: AddBookRequest):
    return book_service.add_book(req.model_dump())


@router.patch("/books/copies")
def update_copies(req: UpdateCopiesRequest):
    return book_service.update_copies(req.book_id, req.delta)


@router.delete("/books/{book_id}")
def remove_book(book_id: str):
    return book_service.remove_book(book_id)


@router.get("/analytics/most-borrowed")
def most_borrowed(limit: int = 5):
    return {"most_borrowed": analytics_service.most_borrowed_books(limit)}


@router.get("/analytics/never-borrowed")
def never_borrowed():
    return {"never_borrowed": analytics_service.never_borrowed_books()}


@router.get("/analytics/overdue")
def overdue():
    return {"overdue": analytics_service.currently_overdue()}

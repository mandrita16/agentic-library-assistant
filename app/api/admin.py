"""
api/admin.py
------------
Administrative catalog and analytics endpoints.

Authentication/authorization will be added through the
admin authentication layer.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import book_service, analytics_service


router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)


class AddBookRequest(BaseModel):
    """Request model for adding a new book."""

    book_id: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=300
    )

    author: str = Field(
        ...,
        min_length=1,
        max_length=200
    )

    isbn: str = Field(
        ...,
        min_length=1,
        max_length=50
    )

    subject: str = Field(
        ...,
        min_length=1,
        max_length=200
    )

    course_codes: list[str] = Field(
        default_factory=list
    )

    description: str = Field(
        ...,
        min_length=1,
        max_length=2000
    )

    shelf_location: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    total_copies: int = Field(
        ...,
        ge=1
    )

    available_copies: int = Field(
        ...,
        ge=0
    )

    tags: list[str] = Field(
        default_factory=list
    )


class UpdateCopiesRequest(BaseModel):
    """Request model for adjusting book copies."""

    book_id: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    delta: int = Field(
        ...,
        description="Positive to add copies, negative to remove copies"
    )


@router.post("/books")
def add_book(req: AddBookRequest):
    """
    Add a new book to MongoDB and ChromaDB.
    """

    if req.available_copies > req.total_copies:
        raise HTTPException(
            status_code=400,
            detail="available_copies cannot exceed total_copies."
        )

    result = book_service.add_book(
        req.model_dump()
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "message",
                "Unable to add book."
            )
        )

    return result


@router.patch("/books/copies")
def update_book_copies(req: UpdateCopiesRequest):
    """
    Atomically adjust total and available copies.
    """

    if req.delta == 0:
        raise HTTPException(
            status_code=400,
            detail="delta cannot be zero."
        )

    result = book_service.update_copies(
        req.book_id,
        req.delta
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get(
                "message",
                "Unable to update copies."
            )
        )

    return result


@router.delete("/books/{book_id}")
def remove_book(book_id: str):
    """
    Remove a book from the catalog.
    """

    result = book_service.remove_book(book_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get(
                "message",
                "Book not found."
            )
        )

    return result


@router.get("/analytics/most-borrowed")
def get_most_borrowed(
    limit: int = Query(
        5,
        ge=1,
        le=50
    )
):
    """
    Return the most frequently borrowed books.
    """

    return {
        "most_borrowed":
            analytics_service.most_borrowed_books(limit)
    }


@router.get("/analytics/never-borrowed")
def get_never_borrowed():
    """
    Return books that have never been borrowed.
    """

    return {
        "never_borrowed":
            analytics_service.never_borrowed_books()
    }


@router.get("/analytics/overdue")
def get_overdue_books():
    """
    Return currently overdue books.
    """

    return {
        "overdue":
            analytics_service.currently_overdue()
    }
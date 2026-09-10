"""
api/books.py
------------
Direct, non-conversational book endpoints — useful for a simple search-bar
UI that doesn't need the agent's reasoning overhead.
"""

from fastapi import APIRouter
from app.rag.vector_store import semantic_search
from app.services import book_service

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/search")
def search(q: str, top_k: int = 5):
    return {"results": semantic_search(q, top_k)}


@router.get("/{book_id}/availability")
def availability(book_id: str):
    result = book_service.get_availability(book_id)
    return result if result else {"error": "Book not found"}

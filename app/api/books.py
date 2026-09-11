"""
api/books.py
------------
Direct book-search and availability endpoints.

These endpoints bypass the conversational agent and are useful
for a search-bar or book-catalog UI.

Semantic search is handled by ChromaDB, while live availability
is retrieved from MongoDB through the book service.
"""

from fastapi import APIRouter, HTTPException, Query

from app.rag.vector_store import semantic_search
from app.services import book_service


router = APIRouter(
    prefix="/books",
    tags=["books"]
)


@router.get("/search")
def search_books(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Semantic search query"
    ),
    top_k: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of search results to return"
    )
):
    """
    Perform semantic search over the library catalog.

    ChromaDB is used here because this endpoint is concerned
    with finding books that are semantically relevant to the
    student's query.
    """

    results = semantic_search(
        q,
        top_k
    )

    return {
        "query": q,
        "results": results
    }


@router.get("/{book_id}/availability")
def get_book_availability(book_id: str):
    """
    Return the live availability information for a book.

    Availability is retrieved from MongoDB because copy counts
    are dynamic and must reflect the current library state.
    """

    result = book_service.get_availability(
        book_id
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Book '{book_id}' not found."
        )

    return result
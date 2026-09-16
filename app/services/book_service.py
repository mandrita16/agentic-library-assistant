"""
app/services/book_service.py
----------------------------

Business logic for the MindSync library catalog.

Responsibilities:

    - Retrieve books from MongoDB
    - Retrieve live availability
    - Perform semantic catalog search
    - Seed the catalog
    - Add books
    - Update copy counts
    - Remove books

Architecture:

    ChromaDB
        ↓
    semantic relevance

    MongoDB
        ↓
    catalog truth + live availability

Recommendation-specific logic belongs in
recommendation_service.py.

Circulation logic belongs in
circulation_service.py.
"""

from pymongo import ReturnDocument

from app.database.mongo import books_collection
from app.rag.vector_store import (
    index_books,
    semantic_search,
)


# ============================================================
# BASIC CATALOG OPERATIONS
# ============================================================


def get_book_by_id(book_id: str) -> dict | None:
    """
    Return a complete book record by its book_id.

    MongoDB is the source of truth for catalog data.
    """

    if not isinstance(book_id, str):
        return None

    book_id = book_id.strip()

    if not book_id:
        return None

    return books_collection.find_one(
        {"book_id": book_id},
        {"_id": 0},
    )


def get_availability(book_id: str) -> dict | None:
    """
    Return live availability information for a book.

    Availability always comes from MongoDB, never ChromaDB.
    """

    if not isinstance(book_id, str):
        return None

    book_id = book_id.strip()

    if not book_id:
        return None

    return books_collection.find_one(
        {"book_id": book_id},
        {
            "_id": 0,
            "book_id": 1,
            "title": 1,
            "available_copies": 1,
            "total_copies": 1,
            "shelf_location": 1,
        },
    )


# ============================================================
# SEMANTIC SEARCH
# ============================================================


def search_books(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Search the library using semantic/vector search.

    ChromaDB determines semantic relevance.

    MongoDB then provides the complete, current book record.

    Old/stale Chroma records that no longer exist in MongoDB
    are ignored.
    """

    if not isinstance(query, str):
        return []

    query = query.strip()

    if not query:
        return []

    if not isinstance(top_k, int):
        top_k = 5

    top_k = max(
        1,
        min(top_k, 20),
    )

    hits = semantic_search(
        query=query,
        top_k=top_k,
    )

    results = []

    for hit in hits:

        book_id = hit.get("book_id")

        if not book_id:
            continue

        # MongoDB is the source of truth.
        book = get_book_by_id(book_id)

        if not book:
            # Chroma may contain an old record that was removed
            # from the MongoDB catalog.
            continue

        results.append(
            {
                "book_id": book.get("book_id"),
                "title": book.get("title"),
                "author": book.get("author"),
                "subject": book.get("subject"),
                "description": book.get("description"),
                "tags": book.get("tags", []),
                "course_codes": book.get("course_codes", []),
                "shelf_location": book.get("shelf_location"),
                "total_copies": book.get(
                    "total_copies",
                    0,
                ),
                "available_copies": book.get(
                    "available_copies",
                    0,
                ),
                "semantic_distance": hit.get(
                    "distance"
                ),
            }
        )

    return results


# ============================================================
# AVAILABILITY
# ============================================================


def get_book_availability(
    book_id: str,
) -> dict | None:
    """
    Get the current live availability of a book.

    This is intentionally separate from semantic search.
    """

    return get_availability(book_id)


def find_best_available_books(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Find semantically relevant books and place currently
    available books before unavailable books.

    Semantic relevance comes from ChromaDB.
    Availability comes from MongoDB.
    """

    results = search_books(
        query=query,
        top_k=top_k,
    )

    available = []
    unavailable = []

    for book in results:

        if book.get("available_copies", 0) > 0:
            available.append(book)

        else:
            unavailable.append(book)

    return available + unavailable


# ============================================================
# CATALOG SEEDING
# ============================================================


def seed_books(
    book_list: list[dict],
) -> None:
    """
    Replace the MongoDB catalog with a supplied book list.

    Used by app.ingest.

    ChromaDB indexing is intentionally handled separately
    by ingest.py.
    """

    if not isinstance(book_list, list):
        raise TypeError(
            "book_list must be a list."
        )

    if not book_list:
        return

    books_collection.delete_many({})

    books_collection.insert_many(
        book_list
    )


# ============================================================
# ADMIN CATALOG OPERATIONS
# ============================================================


def add_book(
    book: dict,
) -> dict:
    """
    Add a new book to MongoDB and immediately index it
    in ChromaDB.
    """

    if not isinstance(book, dict) or not book:
        return {
            "success": False,
            "message": "Book data is required.",
        }

    book_id = book.get("book_id")

    if not isinstance(book_id, str):
        return {
            "success": False,
            "message": "book_id is required.",
        }

    book_id = book_id.strip()

    if not book_id:
        return {
            "success": False,
            "message": "book_id is required.",
        }

    # Store the normalized ID.
    book["book_id"] = book_id

    if books_collection.find_one(
        {"book_id": book_id}
    ):
        return {
            "success": False,
            "message": (
                f"book_id {book_id} already exists."
            ),
        }

    books_collection.insert_one(book)

    # Keep semantic search synchronized.
    index_books([book])

    return {
        "success": True,
        "message": (
            f"Added '{book.get('title', book_id)}' "
            "to the catalog."
        ),
    }


def update_copies(
    book_id: str,
    total_copies_delta: int,
) -> dict:
    """
    Add or remove copies from the catalog.

    Adding copies:
        total_copies increases
        available_copies increases

    Removing copies:
        only currently available copies can be removed.

    This prevents invalid states such as:

        available_copies > total_copies
        available_copies < 0
    """

    if not isinstance(book_id, str):
        return {
            "success": False,
            "message": "book_id is required.",
        }

    book_id = book_id.strip()

    if not book_id:
        return {
            "success": False,
            "message": "book_id is required.",
        }

    if not isinstance(
        total_copies_delta,
        int,
    ):
        return {
            "success": False,
            "message": (
                "total_copies_delta must be an integer."
            ),
        }

    if total_copies_delta == 0:
        return {
            "success": False,
            "message": (
                "total_copies_delta cannot be zero."
            ),
        }

    book = get_book_by_id(book_id)

    if book is None:
        return {
            "success": False,
            "message": "book_id not found.",
        }

    current_total = book.get(
        "total_copies",
        0,
    )

    current_available = book.get(
        "available_copies",
        0,
    )

    # Removing copies.
    if total_copies_delta < 0:

        copies_to_remove = abs(
            total_copies_delta
        )

        if copies_to_remove > current_available:
            return {
                "success": False,
                "message": (
                    f"Cannot remove "
                    f"{copies_to_remove} copies. "
                    f"Only {current_available} "
                    "copies are currently available."
                ),
            }

        if copies_to_remove > current_total:
            return {
                "success": False,
                "message": (
                    "Cannot remove more copies "
                    "than the total catalog count."
                ),
            }

    result = books_collection.find_one_and_update(
        {
            "book_id": book_id,
        },
        {
            "$inc": {
                "total_copies": total_copies_delta,
                "available_copies": total_copies_delta,
            }
        },
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )

    if result is None:
        return {
            "success": False,
            "message": "book_id not found.",
        }

    return {
        "success": True,
        "message": (
            f"'{result['title']}' now has "
            f"{result['total_copies']} total copies "
            f"and {result['available_copies']} "
            "available copies."
        ),
    }


def remove_book(
    book_id: str,
) -> dict:
    """
    Remove a book from the MongoDB catalog.

    Note:
        Circulation-related restrictions should be checked
        before deletion in a production system.
    """

    if not isinstance(book_id, str):
        return {
            "success": False,
            "message": "book_id is required.",
        }

    book_id = book_id.strip()

    if not book_id:
        return {
            "success": False,
            "message": "book_id is required.",
        }

    result = books_collection.delete_one(
        {
            "book_id": book_id,
        }
    )

    if result.deleted_count == 0:
        return {
            "success": False,
            "message": "book_id not found.",
        }

    return {
        "success": True,
        "message": (
            f"Removed {book_id} from the catalog."
        ),
    }
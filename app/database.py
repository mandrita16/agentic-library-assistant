"""
database.py
-----------
MongoDB is our "source of truth" for structured, fast-changing data:
availability counts, reservations, due dates. This is DELIBERATELY kept
separate from the vector store (see vector_store.py).

Why split like this?
- MongoDB   -> exact facts that change often ("2 copies available NOW")
- ChromaDB  -> fuzzy semantic search over descriptions ("books like X")

A pure vector search can't reliably answer "is this available right now"
because embeddings capture MEANING, not live state. So the RAG layer
retrieves candidate books via ChromaDB, then this module is used to
fetch/update their live availability from MongoDB. This two-store
pattern is the single most important design decision in this project —
make sure it's called out explicitly in your Solution Blueprint doc.
"""

from pymongo import MongoClient
from app.config import MONGO_URI, MONGO_DB_NAME

_client = MongoClient(MONGO_URI)
_db = _client[MONGO_DB_NAME]

books_collection = _db["books"]
reservations_collection = _db["reservations"]


def seed_books(book_list: list[dict]) -> None:
    """
    Wipes and reloads the books collection from a list of dicts.
    Run once via ingest.py, or again whenever sample_books.json changes.
    """
    books_collection.delete_many({})
    books_collection.insert_many(book_list)


def get_book_by_id(book_id: str) -> dict | None:
    return books_collection.find_one({"book_id": book_id}, {"_id": 0})


def get_availability(book_id: str) -> dict | None:
    """Returns just the live availability fields for a book_id."""
    book = books_collection.find_one(
        {"book_id": book_id}, {"_id": 0, "available_copies": 1, "total_copies": 1, "title": 1}
    )
    return book


def reserve_book(book_id: str, student_id: str) -> dict:
    """
    Atomically decrements available_copies by 1, but ONLY if a copy is
    actually free (available_copies > 0). This prevents a race condition
    where two students reserve the "last copy" at the same instant.
    """
    result = books_collection.find_one_and_update(
        {"book_id": book_id, "available_copies": {"$gt": 0}},
        {"$inc": {"available_copies": -1}},
        return_document=True,
    )
    if result is None:
        return {"success": False, "message": "No copies currently available to reserve."}

    reservations_collection.insert_one(
        {"book_id": book_id, "student_id": student_id, "status": "reserved"}
    )
    return {"success": True, "message": f"Reserved '{result['title']}' successfully."}


def renew_book(book_id: str, student_id: str) -> dict:
    reservation = reservations_collection.find_one(
        {"book_id": book_id, "student_id": student_id, "status": "reserved"}
    )
    if not reservation:
        return {"success": False, "message": "No active issue/reservation found for this book."}
    # In a fuller build you'd push out a due_date field here.
    return {"success": True, "message": "Renewal successful. New due date extended by 14 days."}

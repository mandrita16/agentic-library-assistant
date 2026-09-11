"""
services/book_service.py
-------------------------
Everything about the book catalog itself: reading it, and (for the admin
agent) adding/updating/removing entries. Circulation state changes
(issue/return/reserve) live in circulation_service.py instead — this
file only owns the catalog record itself.
"""

from app.database.mongo import books_collection
from app.rag.vector_store import index_books


def get_book_by_id(book_id: str) -> dict | None:
    return books_collection.find_one({"book_id": book_id}, {"_id": 0})


def get_availability(book_id: str) -> dict | None:
    return books_collection.find_one(
        {"book_id": book_id},
        {"_id": 0, "title": 1, "available_copies": 1, "total_copies": 1, "shelf_location": 1},
    )


def seed_books(book_list: list[dict]) -> None:
    """Wipes and reloads the whole catalog. Used by ingest.py."""
    books_collection.delete_many({})
    books_collection.insert_many(book_list)


def add_book(book: dict) -> dict:
    """Admin action: add a brand-new title to the catalog AND the vector index, so it's searchable immediately."""
    if books_collection.find_one({"book_id": book["book_id"]}):
        return {"success": False, "message": f"book_id {book['book_id']} already exists."}
    books_collection.insert_one(book)
    index_books([book])  # keep ChromaDB in sync — don't forget this step when adding books manually too
    return {"success": True, "message": f"Added '{book['title']}' to the catalog."}


def update_copies(book_id: str, total_copies_delta: int) -> dict:
    """Admin action: e.g. library buys 2 more copies -> total_copies_delta=+2 (also bumps available_copies)."""
    result = books_collection.find_one_and_update(
        {"book_id": book_id},
        {"$inc": {"total_copies": total_copies_delta, "available_copies": total_copies_delta}},
        return_document=True,
    )
    if result is None:
        return {"success": False, "message": "book_id not found."}
    return {"success": True, "message": f"'{result['title']}' now has {result['total_copies']} total copies."}


def remove_book(book_id: str) -> dict:
    result = books_collection.delete_one({"book_id": book_id})
    if result.deleted_count == 0:
        return {"success": False, "message": "book_id not found."}
    return {"success": True, "message": f"Removed {book_id} from the catalog."}

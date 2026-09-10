"""
services/analytics_service.py
-------------------------------
Simple MongoDB aggregation queries for the admin dashboard. Kept
intentionally lightweight (no separate analytics DB/warehouse needed —
this is exactly the kind of thing MongoDB's aggregation pipeline is
good at for a project this size).

Note: "most searched subjects" would need search queries to be logged
somewhere first — that's a genuine future enhancement (see README),
not implemented here since it needs a new `search_log` collection and
a bit of design (do we log every /search call? every agent tool call?).
"""

from app.database.mongo import books_collection, borrow_records_collection


def most_borrowed_books(limit: int = 5) -> list[dict]:
    pipeline = [
        {"$group": {"_id": "$book_id", "borrow_count": {"$sum": 1}}},
        {"$sort": {"borrow_count": -1}},
        {"$limit": limit},
    ]
    results = list(borrow_records_collection.aggregate(pipeline))
    for r in results:
        book = books_collection.find_one({"book_id": r["_id"]}, {"_id": 0, "title": 1})
        r["title"] = book["title"] if book else "Unknown"
    return results


def never_borrowed_books() -> list[dict]:
    borrowed_ids = borrow_records_collection.distinct("book_id")
    return list(
        books_collection.find({"book_id": {"$nin": borrowed_ids}}, {"_id": 0, "book_id": 1, "title": 1})
    )


def currently_overdue() -> list[dict]:
    from datetime import datetime

    return list(
        borrow_records_collection.find(
            {"status": "issued", "due_date": {"$lt": datetime.utcnow()}},
            {"_id": 0},
        )
    )

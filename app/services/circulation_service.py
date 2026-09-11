"""
services/circulation_service.py
--------------------------------
The heart of "AI Library Management System" vs. the earlier simple demo:
issue/return/renew with due dates, a reservation WAITLIST (not just a
single reserve-or-fail), and renewal eligibility rules. All the atomic
MongoDB updates (find_one_and_update with a filter condition) exist to
prevent race conditions — e.g. two students can't issue the "last copy"
at the same instant.
"""

import uuid
from datetime import datetime, timedelta
from app.config import LOAN_PERIOD_DAYS, MAX_RENEWALS
from app.database.mongo import books_collection, borrow_records_collection, reservations_collection
from app.services.fine_service import calculate_overdue_fine, add_fine_to_student


def issue_book(book_id: str, student_id: str) -> dict:
    book = books_collection.find_one_and_update(
        {"book_id": book_id, "available_copies": {"$gt": 0}},
        {"$inc": {"available_copies": -1}},
        return_document=True,
    )
    if book is None:
        return {
            "success": False,
            "message": "No copies currently available. Use reserve_book to join the waitlist instead.",
        }

    now = datetime.utcnow()
    due_date = now + timedelta(days=LOAN_PERIOD_DAYS)
    record_id = str(uuid.uuid4())
    borrow_records_collection.insert_one(
        {
            "record_id": record_id,
            "book_id": book_id,
            "student_id": student_id,
            "issue_date": now,
            "due_date": due_date,
            "return_date": None,
            "status": "issued",
            "renewal_count": 0,
        }
    )
    return {
        "success": True,
        "message": f"Issued '{book['title']}'. Due back by {due_date.strftime('%d %b %Y')}.",
        "record_id": record_id,
        "due_date": due_date.isoformat(),
    }


def return_book(book_id: str, student_id: str) -> dict:
    record = borrow_records_collection.find_one(
        {"book_id": book_id, "student_id": student_id, "status": "issued"}
    )
    if record is None:
        return {"success": False, "message": "No active issued record found for this book and student."}

    now = datetime.utcnow()
    fine = calculate_overdue_fine(record["due_date"], now)

    borrow_records_collection.update_one(
        {"record_id": record["record_id"]},
        {"$set": {"return_date": now, "status": "returned"}},
    )

    if fine > 0:
        add_fine_to_student(student_id, fine)

    # Give the copy back to the shelf...
    books_collection.update_one({"book_id": book_id}, {"$inc": {"available_copies": 1}})

    # ...unless someone is waiting for it — then flag the next person in queue as "ready".
    next_in_line = reservations_collection.find_one_and_update(
        {"book_id": book_id, "status": "waiting"},
        {"$set": {"status": "ready"}},
        sort=[("queue_position", 1)],
        return_document=True,
    )

    message = "Book returned."
    if fine > 0:
        message += f" Overdue fine of ₹{fine} added to your account."
    if next_in_line:
        message += f" Notifying student {next_in_line['student_id']} — their reservation is now ready for pickup."

    return {"success": True, "message": message, "fine_charged": fine}


def renew_book(book_id: str, student_id: str) -> dict:
    record = borrow_records_collection.find_one(
        {"book_id": book_id, "student_id": student_id, "status": "issued"}
    )
    if record is None:
        return {"success": False, "message": "No active issued record found for this book and student."}

    if record["renewal_count"] >= MAX_RENEWALS:
        return {"success": False, "message": f"Maximum renewals ({MAX_RENEWALS}) already reached for this issue."}

    someone_waiting = reservations_collection.find_one({"book_id": book_id, "status": "waiting"})
    if someone_waiting:
        return {"success": False, "message": "Cannot renew — another student is waiting for this book."}

    new_due_date = record["due_date"] + timedelta(days=LOAN_PERIOD_DAYS)
    borrow_records_collection.update_one(
        {"record_id": record["record_id"]},
        {"$set": {"due_date": new_due_date}, "$inc": {"renewal_count": 1}},
    )
    return {
        "success": True,
        "message": f"Renewed. New due date: {new_due_date.strftime('%d %b %Y')}.",
        "due_date": new_due_date.isoformat(),
    }


def reserve_book(book_id: str, student_id: str) -> dict:
    """Join the waitlist. Only makes sense when the book currently has zero available copies — if copies ARE free, the agent should call issue_book instead."""
    book = books_collection.find_one({"book_id": book_id})
    if book is None:
        return {"success": False, "message": "book_id not found."}
    if book["available_copies"] > 0:
        return {"success": False, "message": "Copies are currently available — use issue_book instead of reserving."}

    already_waiting = reservations_collection.find_one(
        {"book_id": book_id, "student_id": student_id, "status": "waiting"}
    )
    if already_waiting:
        return {"success": False, "message": f"Already on the waitlist at position {already_waiting['queue_position']}."}

    current_queue_length = reservations_collection.count_documents({"book_id": book_id, "status": "waiting"})
    queue_position = current_queue_length + 1

    reservations_collection.insert_one(
        {
            "reservation_id": str(uuid.uuid4()),
            "book_id": book_id,
            "student_id": student_id,
            "status": "waiting",
            "queue_position": queue_position,
            "created_at": datetime.utcnow(),
        }
    )
    return {"success": True, "message": f"Added to waitlist at position {queue_position}. You'll be notified when it's ready."}


def cancel_reservation(book_id: str, student_id: str) -> dict:
    result = reservations_collection.find_one_and_update(
        {"book_id": book_id, "student_id": student_id, "status": {"$in": ["waiting", "ready"]}},
        {"$set": {"status": "cancelled"}},
    )
    if result is None:
        return {"success": False, "message": "No active reservation found to cancel."}

    # Shift everyone behind this student up by one position.
    reservations_collection.update_many(
        {"book_id": book_id, "status": "waiting", "queue_position": {"$gt": result["queue_position"]}},
        {"$inc": {"queue_position": -1}},
    )
    return {"success": True, "message": "Reservation cancelled."}

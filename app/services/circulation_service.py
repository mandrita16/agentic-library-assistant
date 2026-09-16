"""
services/circulation_service.py
--------------------------------

Library circulation business logic:

- Issue books
- Return books
- Renew books
- Reserve unavailable books
- Cancel reservations
- Due-date handling
- Waitlist handling
- Overdue fines

MongoDB is the source of truth for circulation state.

Catalog information is handled by book_service.py.
"""

import uuid
from datetime import datetime, timedelta

from pymongo import ReturnDocument

from app.config import LOAN_PERIOD_DAYS, MAX_RENEWALS
from app.database.mongo import (
    books_collection,
    borrow_records_collection,
    reservations_collection,
)
from app.services.fine_service import (
    calculate_overdue_fine,
    add_fine_to_student,
)


# ============================================================
# ISSUE BOOK
# ============================================================


def issue_book(book_id: str, student_id: str) -> dict:
    """
    Issue one available copy of a book to a student.

    Rules:
    - Book must exist.
    - A copy must be available.
    - Student must not already have the same book issued.
    """

    if not book_id or not book_id.strip():
        return {
            "success": False,
            "message": "book_id is required.",
        }

    if not student_id or not student_id.strip():
        return {
            "success": False,
            "message": "student_id is required.",
        }

    book_id = book_id.strip()
    student_id = student_id.strip()

    # --------------------------------------------------------
    # Prevent duplicate active borrowing
    # --------------------------------------------------------

    existing_record = borrow_records_collection.find_one(
        {
            "book_id": book_id,
            "student_id": student_id,
            "status": "issued",
        }
    )

    if existing_record:
        return {
            "success": False,
            "message": "You already have this book issued.",
        }

    # --------------------------------------------------------
    # Check whether the student has a READY reservation
    # --------------------------------------------------------

    ready_reservation = reservations_collection.find_one(
        {
            "book_id": book_id,
            "student_id": student_id,
            "status": "ready",
        }
    )

    # --------------------------------------------------------
    # If another student's reservation is ready, don't allow
    # an unrelated student to take the held copy.
    # --------------------------------------------------------

    other_ready_reservation = reservations_collection.find_one(
        {
            "book_id": book_id,
            "status": "ready",
            "student_id": {"$ne": student_id},
        }
    )

    if other_ready_reservation and not ready_reservation:
        return {
            "success": False,
            "message": (
                "This book is currently being held for another "
                "student with a reservation."
            ),
        }

    # --------------------------------------------------------
    # Atomically claim one available copy
    # --------------------------------------------------------

    book = books_collection.find_one_and_update(
        {
            "book_id": book_id,
            "available_copies": {"$gt": 0},
        },
        {
            "$inc": {"available_copies": -1},
        },
        return_document=ReturnDocument.AFTER,
    )

    if book is None:
        return {
            "success": False,
            "message": (
                "No copies currently available. "
                "Use reserve_book to join the waitlist instead."
            ),
        }

    # --------------------------------------------------------
    # Create borrowing record
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Consume ready reservation if this issue fulfilled it
    # --------------------------------------------------------

    if ready_reservation:
        reservations_collection.update_one(
            {
                "reservation_id": ready_reservation["reservation_id"],
                "status": "ready",
            },
            {
                "$set": {
                    "status": "fulfilled",
                    "fulfilled_at": now,
                }
            },
        )

    return {
        "success": True,
        "message": (
            f"Issued '{book['title']}'. "
            f"Due back by {due_date.strftime('%d %b %Y')}."
        ),
        "record_id": record_id,
        "due_date": due_date.isoformat(),
    }


# ============================================================
# RETURN BOOK
# ============================================================


def return_book(book_id: str, student_id: str) -> dict:
    """
    Return a book currently issued to the authenticated student.

    Calculates overdue fine and moves the next waiting reservation
    to READY status.
    """

    if not book_id or not book_id.strip():
        return {
            "success": False,
            "message": "book_id is required.",
        }

    if not student_id or not student_id.strip():
        return {
            "success": False,
            "message": "student_id is required.",
        }

    book_id = book_id.strip()
    student_id = student_id.strip()

    # --------------------------------------------------------
    # Atomically mark the active borrowing record as returned
    # --------------------------------------------------------

    now = datetime.utcnow()

    record = borrow_records_collection.find_one_and_update(
        {
            "book_id": book_id,
            "student_id": student_id,
            "status": "issued",
        },
        {
            "$set": {
                "return_date": now,
                "status": "returned",
            }
        },
        return_document=ReturnDocument.BEFORE,
    )

    if record is None:
        return {
            "success": False,
            "message": (
                "No active issued record found "
                "for this book and student."
            ),
        }

    # --------------------------------------------------------
    # Calculate fine
    # --------------------------------------------------------

    fine = calculate_overdue_fine(
        record["due_date"],
        now,
    )

    if fine > 0:
        add_fine_to_student(
            student_id,
            fine,
        )

    # --------------------------------------------------------
    # Return physical copy
    # --------------------------------------------------------

    books_collection.update_one(
        {"book_id": book_id},
        {
            "$inc": {
                "available_copies": 1,
            }
        },
    )

    # --------------------------------------------------------
    # Promote the first waiting reservation
    # --------------------------------------------------------

    next_in_line = reservations_collection.find_one_and_update(
        {
            "book_id": book_id,
            "status": "waiting",
        },
        {
            "$set": {
                "status": "ready",
                "ready_at": now,
            }
        },
        sort=[
            ("queue_position", 1),
            ("created_at", 1),
        ],
        return_document=ReturnDocument.AFTER,
    )

    message = "Book returned successfully."

    if fine > 0:
        message += (
            f" Overdue fine of ₹{fine} "
            f"added to your account."
        )

    if next_in_line:
        message += (
            f" The book is now ready for the next student "
            f"in the reservation queue."
        )

    return {
        "success": True,
        "message": message,
        "fine_charged": fine,
    }


# ============================================================
# RENEW BOOK
# ============================================================


def renew_book(book_id: str, student_id: str) -> dict:
    """
    Renew an active borrowing record.

    Renewal is denied when:
    - The student doesn't currently have the book.
    - Maximum renewals have been reached.
    - Another student is waiting for the book.
    """

    if not book_id or not book_id.strip():
        return {
            "success": False,
            "message": "book_id is required.",
        }

    if not student_id or not student_id.strip():
        return {
            "success": False,
            "message": "student_id is required.",
        }

    book_id = book_id.strip()
    student_id = student_id.strip()

    record = borrow_records_collection.find_one(
        {
            "book_id": book_id,
            "student_id": student_id,
            "status": "issued",
        }
    )

    if record is None:
        return {
            "success": False,
            "message": (
                "No active issued record found "
                "for this book and student."
            ),
        }

    if record.get("renewal_count", 0) >= MAX_RENEWALS:
        return {
            "success": False,
            "message": (
                f"Maximum renewals ({MAX_RENEWALS}) "
                "already reached for this issue."
            ),
        }

    # --------------------------------------------------------
    # Waiting students prevent renewal
    # --------------------------------------------------------

    someone_waiting = reservations_collection.find_one(
        {
            "book_id": book_id,
            "status": "waiting",
        }
    )

    if someone_waiting:
        return {
            "success": False,
            "message": (
                "Cannot renew — another student "
                "is waiting for this book."
            ),
        }

    # --------------------------------------------------------
    # Atomic renewal update
    # --------------------------------------------------------

    new_due_date = (
        record["due_date"]
        + timedelta(days=LOAN_PERIOD_DAYS)
    )

    updated_record = borrow_records_collection.find_one_and_update(
        {
            "record_id": record["record_id"],
            "status": "issued",
            "renewal_count": {
                "$lt": MAX_RENEWALS,
            },
        },
        {
            "$set": {
                "due_date": new_due_date,
            },
            "$inc": {
                "renewal_count": 1,
            },
        },
        return_document=ReturnDocument.AFTER,
    )

    if updated_record is None:
        return {
            "success": False,
            "message": (
                "Renewal could not be completed. "
                "The borrowing record may have changed."
            ),
        }

    return {
        "success": True,
        "message": (
            f"Renewed successfully. "
            f"New due date: "
            f"{new_due_date.strftime('%d %b %Y')}."
        ),
        "due_date": new_due_date.isoformat(),
        "renewal_count": updated_record["renewal_count"],
    }


# ============================================================
# RESERVE BOOK
# ============================================================


def reserve_book(book_id: str, student_id: str) -> dict:
    """
    Add a student to the reservation waitlist.

    Reservation is allowed only when no copies are currently
    available.
    """

    if not book_id or not book_id.strip():
        return {
            "success": False,
            "message": "book_id is required.",
        }

    if not student_id or not student_id.strip():
        return {
            "success": False,
            "message": "student_id is required.",
        }

    book_id = book_id.strip()
    student_id = student_id.strip()

    book = books_collection.find_one(
        {"book_id": book_id}
    )

    if book is None:
        return {
            "success": False,
            "message": "book_id not found.",
        }

    if book.get("available_copies", 0) > 0:
        return {
            "success": False,
            "message": (
                "Copies are currently available — "
                "use issue_book instead of reserving."
            ),
        }

    # --------------------------------------------------------
    # Prevent duplicate active reservation
    # --------------------------------------------------------

    existing = reservations_collection.find_one(
        {
            "book_id": book_id,
            "student_id": student_id,
            "status": {
                "$in": ["waiting", "ready"],
            },
        }
    )

    if existing:
        return {
            "success": False,
            "message": (
                f"Already reserved. "
                f"Current status: {existing['status']}."
            ),
        }

    # --------------------------------------------------------
    # Determine next queue position
    # --------------------------------------------------------

    last_reservation = reservations_collection.find_one(
        {
            "book_id": book_id,
            "status": "waiting",
        },
        sort=[
            ("queue_position", -1),
        ],
    )

    if last_reservation:
        queue_position = (
            last_reservation["queue_position"] + 1
        )
    else:
        queue_position = 1

    # --------------------------------------------------------
    # Create reservation
    # --------------------------------------------------------

    reservation_id = str(uuid.uuid4())
    now = datetime.utcnow()

    reservations_collection.insert_one(
        {
            "reservation_id": reservation_id,
            "book_id": book_id,
            "student_id": student_id,
            "status": "waiting",
            "queue_position": queue_position,
            "created_at": now,
        }
    )

    return {
        "success": True,
        "message": (
            f"Added to the waitlist at position "
            f"{queue_position}. "
            "You'll be notified when the book is ready."
        ),
        "reservation_id": reservation_id,
        "queue_position": queue_position,
    }


# ============================================================
# CANCEL RESERVATION
# ============================================================


def cancel_reservation(
    book_id: str,
    student_id: str,
) -> dict:
    """
    Cancel an active reservation.

    Waiting reservations are removed from the active queue.
    Ready reservations are also cancelled.
    """

    if not book_id or not book_id.strip():
        return {
            "success": False,
            "message": "book_id is required.",
        }

    if not student_id or not student_id.strip():
        return {
            "success": False,
            "message": "student_id is required.",
        }

    book_id = book_id.strip()
    student_id = student_id.strip()

    reservation = reservations_collection.find_one_and_update(
        {
            "book_id": book_id,
            "student_id": student_id,
            "status": {
                "$in": ["waiting", "ready"],
            },
        },
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": datetime.utcnow(),
            }
        },
        return_document=ReturnDocument.BEFORE,
    )

    if reservation is None:
        return {
            "success": False,
            "message": (
                "No active reservation found to cancel."
            ),
        }

    # --------------------------------------------------------
    # Only waiting reservations occupy queue positions.
    # --------------------------------------------------------

    if reservation["status"] == "waiting":
        # Remove the cancelled student from the active waitlist order.
        reservations_collection.update_many(
            {
                "book_id": book_id,
                "status": "waiting",
                "queue_position": {
                    "$gt": reservation["queue_position"],
                },
            },
            {
                "$inc": {
                    "queue_position": -1,
                }
            },
        )

    elif reservation["status"] == "ready":
        # A ready reservation owns the currently available copy. If that
        # student cancels, the copy should be offered to the next student
        # in the waiting queue instead of leaving the queue inconsistent.
        next_in_line = reservations_collection.find_one_and_update(
            {
                "book_id": book_id,
                "status": "waiting",
            },
            {
                "$set": {
                    "status": "ready",
                    "ready_at": datetime.utcnow(),
                }
            },
            sort=[
                ("queue_position", 1),
                ("created_at", 1),
            ],
            return_document=ReturnDocument.AFTER,
        )

        # The ready reservation is no longer consuming a reservation slot.
        # Compact the remaining waiting positions so the queue stays clean.
        if next_in_line:
            reservations_collection.update_many(
                {
                    "book_id": book_id,
                    "status": "waiting",
                    "queue_position": {
                        "$gt": next_in_line["queue_position"],
                    },
                },
                {
                    "$inc": {
                        "queue_position": -1,
                    }
                },
            )

    return {
        "success": True,
        "message": "Reservation cancelled successfully.",
    }


# ============================================================
# DUE SOON
# ============================================================


def get_due_soon_books(
    student_id: str,
    days: int = 3,
) -> list[dict]:
    """
    Return books currently issued to a student that are due
    within the next `days` days.
    """

    if not student_id or not student_id.strip():
        return []

    days = max(0, min(days, 30))

    now = datetime.utcnow()
    deadline = now + timedelta(days=days)

    records = borrow_records_collection.find(
        {
            "student_id": student_id.strip(),
            "status": "issued",
            "due_date": {
                "$gte": now,
                "$lte": deadline,
            },
        },
        {
            "_id": 0,
        },
    )

    results = []

    for record in records:
        results.append(record)

    return results
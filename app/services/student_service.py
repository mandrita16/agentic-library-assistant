"""
services/student_service.py
---------------------------

Read-only aggregation service for the student's dashboard.

This service does not create or modify circulation state.

It combines information from:

- borrow_records
- reservations
- student fine balance

into one student-specific dashboard.
"""

from datetime import datetime, timedelta

from app.database.mongo import (
    borrow_records_collection,
    reservations_collection,
)
from app.services.fine_service import (
    get_outstanding_fine,
    calculate_overdue_fine,
)


# ============================================================
# STUDENT DASHBOARD
# ============================================================


def get_dashboard(student_id: str) -> dict:
    """
    Build the dashboard for an authenticated student.

    Includes:

    - currently borrowed books
    - due dates
    - current overdue fine for each borrowed book
    - books due within the next 3 days
    - active reservations
    - outstanding fine
    """

    if not student_id or not student_id.strip():
        return {
            "success": False,
            "message": "student_id is required.",
        }

    student_id = student_id.strip()

    now = datetime.utcnow()
    due_soon_deadline = now + timedelta(days=3)

    # --------------------------------------------------------
    # Currently borrowed books
    # --------------------------------------------------------

    borrowed = list(
        borrow_records_collection.find(
            {
                "student_id": student_id,
                "status": "issued",
            },
            {
                "_id": 0,
            },
        )
    )

    # --------------------------------------------------------
    # Calculate due-soon information
    # --------------------------------------------------------

    due_soon_count = 0
    overdue_count = 0

    for record in borrowed:

        due_date = record.get("due_date")

        if not due_date:
            record["current_overdue_fine"] = 0.0
            continue

        # Fine if the student returned the book right now.
        current_fine = calculate_overdue_fine(
            due_date,
            now,
        )

        record["current_overdue_fine"] = current_fine

        # Overdue
        if due_date < now:
            overdue_count += 1

        # Due today or within the next 3 days
        elif due_date <= due_soon_deadline:
            due_soon_count += 1

    # --------------------------------------------------------
    # Active reservations
    # --------------------------------------------------------

    reservations = list(
        reservations_collection.find(
            {
                "student_id": student_id,
                "status": {
                    "$in": [
                        "waiting",
                        "ready",
                    ]
                },
            },
            {
                "_id": 0,
            },
        )
    )

    # --------------------------------------------------------
    # Outstanding fine
    # --------------------------------------------------------

    outstanding_fine = get_outstanding_fine(
        student_id
    )

    # --------------------------------------------------------
    # Final dashboard
    # --------------------------------------------------------

    return {
        "success": True,
        "student_id": student_id,

        "books_borrowed": len(borrowed),
        "borrowed_details": borrowed,

        "due_soon": due_soon_count,
        "overdue_books": overdue_count,

        "active_reservations": len(reservations),
        "reservation_details": reservations,

        "outstanding_fine": outstanding_fine,
    }
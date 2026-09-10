"""
services/student_service.py
-----------------------------
Aggregates data that ALREADY lives in other collections (borrow_records,
reservations, students) into one dashboard view. Deliberately has no
new state of its own — it's a read-only rollup.
"""

from app.database.mongo import borrow_records_collection, reservations_collection
from app.services.fine_service import get_outstanding_fine, calculate_overdue_fine


def get_dashboard(student_id: str) -> dict:
    borrowed = list(
        borrow_records_collection.find({"student_id": student_id, "status": "issued"}, {"_id": 0})
    )

    due_soon_count = 0
    for record in borrowed:
        # Flag anything overdue OR due within the next 3 days as "due soon".
        current_fine_if_returned_today = calculate_overdue_fine(record["due_date"])
        record["current_overdue_fine"] = current_fine_if_returned_today
        if current_fine_if_returned_today > 0:
            due_soon_count += 1

    reservations = list(
        reservations_collection.find(
            {"student_id": student_id, "status": {"$in": ["waiting", "ready"]}}, {"_id": 0}
        )
    )

    return {
        "student_id": student_id,
        "books_borrowed": len(borrowed),
        "borrowed_details": borrowed,
        "due_soon": due_soon_count,
        "active_reservations": len(reservations),
        "reservation_details": reservations,
        "outstanding_fine": get_outstanding_fine(student_id),
    }

"""
services/fine_service.py
-------------------------
Fine math lives here, isolated from circulation_service.py, so the
"how much is this fine" question can be reused for the dashboard,
the return flow, and any future payment-status endpoint without
duplicating the calculation.
"""

from datetime import datetime
from app.config import FINE_PER_DAY
from app.database.mongo import students_collection


def calculate_overdue_fine(due_date: datetime, return_date: datetime | None = None) -> float:
    """
    Fine for a single borrow record. If return_date is None, calculates
    the fine AS OF NOW (for a still-issued, possibly-overdue book) — used
    by the dashboard to show "you'll owe X if you don't return today."
    """
    compare_date = return_date or datetime.utcnow()
    overdue_days = (compare_date - due_date).days
    if overdue_days <= 0:
        return 0.0
    return round(overdue_days * FINE_PER_DAY, 2)


def add_fine_to_student(student_id: str, amount: float) -> None:
    if amount <= 0:
        return
    students_collection.update_one(
        {"student_id": student_id},
        {"$inc": {"outstanding_fine": amount}},
        upsert=True,
    )


def get_outstanding_fine(student_id: str) -> float:
    student = students_collection.find_one({"student_id": student_id}, {"_id": 0, "outstanding_fine": 1})
    return student.get("outstanding_fine", 0.0) if student else 0.0


def pay_fine(student_id: str, amount: float) -> dict:
    current = get_outstanding_fine(student_id)
    if amount > current:
        return {"success": False, "message": f"Amount exceeds outstanding fine of ₹{current}."}
    students_collection.update_one({"student_id": student_id}, {"$inc": {"outstanding_fine": -amount}}, upsert=True)
    return {"success": True, "message": f"₹{amount} paid. Remaining balance: ₹{round(current - amount, 2)}."}

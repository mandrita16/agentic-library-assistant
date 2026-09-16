"""
app/services/fine_service.py
----------------------------

All fine-related calculations and balance operations live here.

This keeps fine logic separate from circulation_service.py so
the same functionality can be reused by:

    - Return flow
    - Student dashboard
    - Due-date assistance
    - Future payment-status endpoints
"""

from datetime import datetime

from app.config import FINE_PER_DAY
from app.database.mongo import students_collection


# ============================================================
# FINE CALCULATION
# ============================================================


def calculate_overdue_fine(
    due_date: datetime,
    return_date: datetime | None = None,
) -> float:
    """
    Calculate the overdue fine for a single borrow record.

    If return_date is None, calculate the fine as of the
    current time.

    Fine = overdue days × FINE_PER_DAY
    """

    if due_date is None:
        return 0.0

    compare_date = (
        return_date
        if return_date is not None
        else datetime.utcnow()
    )

    overdue_days = (
        compare_date - due_date
    ).days

    if overdue_days <= 0:
        return 0.0

    return round(
        overdue_days * FINE_PER_DAY,
        2,
    )


# ============================================================
# ADD FINE
# ============================================================


def add_fine_to_student(
    student_id: str,
    amount: float,
) -> None:
    """
    Add a fine to an existing student's outstanding balance.

    Invalid or non-positive amounts are ignored.
    """

    if not isinstance(student_id, str):
        return

    student_id = student_id.strip()

    if not student_id:
        return

    if not isinstance(amount, (int, float)):
        return

    if amount <= 0:
        return

    amount = round(float(amount), 2)

    students_collection.update_one(
        {
            "student_id": student_id,
        },
        {
            "$inc": {
                "outstanding_fine": amount,
            }
        },
    )


# ============================================================
# GET OUTSTANDING FINE
# ============================================================


def get_outstanding_fine(
    student_id: str,
) -> float:
    """
    Return the student's current outstanding fine.
    """

    if not isinstance(student_id, str):
        return 0.0

    student_id = student_id.strip()

    if not student_id:
        return 0.0

    student = students_collection.find_one(
        {
            "student_id": student_id,
        },
        {
            "_id": 0,
            "outstanding_fine": 1,
        },
    )

    if not student:
        return 0.0

    return round(
        float(
            student.get(
                "outstanding_fine",
                0.0,
            )
        ),
        2,
    )


# ============================================================
# PAY FINE
# ============================================================


def pay_fine(
    student_id: str,
    amount: float,
) -> dict:
    """
    Reduce the student's outstanding fine.

    Payment must:

        - have a valid student ID
        - be greater than zero
        - not exceed the current outstanding balance
    """

    if not isinstance(student_id, str):
        return {
            "success": False,
            "message": "student_id is required.",
        }

    student_id = student_id.strip()

    if not student_id:
        return {
            "success": False,
            "message": "student_id is required.",
        }

    if not isinstance(amount, (int, float)):
        return {
            "success": False,
            "message": "Payment amount must be numeric.",
        }

    if amount <= 0:
        return {
            "success": False,
            "message": (
                "Payment amount must be greater than zero."
            ),
        }

    amount = round(
        float(amount),
        2,
    )

    current = get_outstanding_fine(
        student_id
    )

    if amount > current:
        return {
            "success": False,
            "message": (
                f"Amount exceeds outstanding fine "
                f"of ₹{current:.2f}."
            ),
        }

    result = students_collection.update_one(
        {
            "student_id": student_id,
            "outstanding_fine": {
                "$gte": amount,
            },
        },
        {
            "$inc": {
                "outstanding_fine": -amount,
            }
        },
    )

    if result.modified_count == 0:
        return {
            "success": False,
            "message": (
                "Fine payment could not be completed. "
                "The balance may have changed."
            ),
        }

    remaining = round(
        current - amount,
        2,
    )

    return {
        "success": True,
        "message": (
            f"₹{amount:.2f} paid successfully. "
            f"Remaining balance: ₹{remaining:.2f}."
        ),
        "amount_paid": amount,
        "remaining_balance": remaining,
    }
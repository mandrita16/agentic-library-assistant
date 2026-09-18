"""
app/services/fine_service.py
----------------------------

Fine-related calculations and balance operations.

Responsibilities:
- Calculate overdue fines
- Add fines to student accounts
- Get outstanding fine balance
- Pay outstanding fines

Business logic remains separate from:
- agent.py
- tools.py
- API routes

This service can be reused by:
- Return flow
- Student dashboard
- Due-date assistance
- Fine/payment endpoints
- MindSync agent
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
    Calculate the overdue fine for a borrow record.

    Fine:
        overdue days × FINE_PER_DAY

    If return_date is None, the fine is calculated
    using the current UTC time.

    Returns:
        float: calculated fine amount
    """

    if due_date is None:
        return 0.0

    # --------------------------------------------------------
    # Determine comparison date
    # --------------------------------------------------------

    compare_date = (
        return_date
        if return_date is not None
        else datetime.utcnow()
    )

    # --------------------------------------------------------
    # Calculate overdue days
    # --------------------------------------------------------

    overdue_days = (
        compare_date - due_date
    ).days

    if overdue_days <= 0:
        return 0.0

    # --------------------------------------------------------
    # Calculate fine
    # --------------------------------------------------------

    fine = (
        overdue_days * FINE_PER_DAY
    )

    return round(
        float(fine),
        2,
    )


# ============================================================
# ADD FINE
# ============================================================

def add_fine_to_student(
    student_id: str,
    amount: float,
) -> dict:
    """
    Add a fine to a student's outstanding balance.

    Returns a structured result instead of silently
    failing so callers can handle the result safely.
    """

    # --------------------------------------------------------
    # Validate student ID
    # --------------------------------------------------------

    if not isinstance(
        student_id,
        str,
    ):
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

    # --------------------------------------------------------
    # Validate amount
    # --------------------------------------------------------

    if not isinstance(
        amount,
        (int, float),
    ):
        return {
            "success": False,
            "message": "Fine amount must be numeric.",
        }

    if amount <= 0:
        return {
            "success": False,
            "message": (
                "Fine amount must be greater than zero."
            ),
        }

    amount = round(
        float(amount),
        2,
    )

    # --------------------------------------------------------
    # Update student balance
    # --------------------------------------------------------

    result = students_collection.update_one(
        {
            "student_id": student_id,
        },
        {
            "$inc": {
                "outstanding_fine": amount,
            }
        },
    )

    # --------------------------------------------------------
    # Verify student exists
    # --------------------------------------------------------

    if result.matched_count == 0:
        return {
            "success": False,
            "message": (
                f"Student {student_id} was not found."
            ),
        }

    # --------------------------------------------------------
    # Get updated balance
    # --------------------------------------------------------

    new_balance = get_outstanding_fine(
        student_id
    )

    return {
        "success": True,
        "message": (
            f"₹{amount:.2f} fine added successfully."
        ),
        "amount_added": amount,
        "outstanding_balance": new_balance,
    }


# ============================================================
# GET OUTSTANDING FINE
# ============================================================

def get_outstanding_fine(
    student_id: str,
) -> float:
    """
    Return the student's current outstanding fine.

    Returns:
        float: outstanding fine balance
    """

    if not isinstance(
        student_id,
        str,
    ):
        return 0.0

    student_id = student_id.strip()

    if not student_id:
        return 0.0

    # --------------------------------------------------------
    # Find student
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Safely convert balance
    # --------------------------------------------------------

    try:
        balance = float(
            student.get(
                "outstanding_fine",
                0.0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        balance = 0.0

    return round(
        max(balance, 0.0),
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
    Pay part or all of a student's outstanding fine.

    Payment must:
        - have a valid student ID
        - be numeric
        - be greater than zero
        - not exceed the outstanding balance

    Returns:
        dict containing payment result and remaining balance.
    """

    # --------------------------------------------------------
    # Validate student ID
    # --------------------------------------------------------

    if not isinstance(
        student_id,
        str,
    ):
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

    # --------------------------------------------------------
    # Validate payment amount
    # --------------------------------------------------------

    if not isinstance(
        amount,
        (int, float),
    ):
        return {
            "success": False,
            "message": (
                "Payment amount must be numeric."
            ),
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

    # --------------------------------------------------------
    # Get current balance
    # --------------------------------------------------------

    current_balance = get_outstanding_fine(
        student_id
    )

    # --------------------------------------------------------
    # Check balance
    # --------------------------------------------------------

    if current_balance <= 0:
        return {
            "success": False,
            "message": (
                "You do not have any outstanding fine."
            ),
        }

    # --------------------------------------------------------
    # Prevent overpayment
    # --------------------------------------------------------

    if amount > current_balance:
        return {
            "success": False,
            "message": (
                f"Payment amount exceeds the "
                f"outstanding fine of "
                f"₹{current_balance:.2f}."
            ),
            "outstanding_balance": current_balance,
        }

    # --------------------------------------------------------
    # Atomic balance update
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Check whether update succeeded
    # --------------------------------------------------------

    if result.modified_count == 0:
        return {
            "success": False,
            "message": (
                "Fine payment could not be completed. "
                "The balance may have changed."
            ),
        }

    # --------------------------------------------------------
    # Get actual remaining balance
    # --------------------------------------------------------

    remaining_balance = get_outstanding_fine(
        student_id
    )

    return {
        "success": True,
        "message": (
            f"₹{amount:.2f} paid successfully."
        ),
        "amount_paid": amount,
        "remaining_balance": remaining_balance,
    }
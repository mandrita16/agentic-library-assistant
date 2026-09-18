"""
app/agent/tools.py

MindSync LangGraph tools.

Responsibilities:
- Expose library functionality to the AI agent
- Validate tool inputs
- Call business logic from app/services/
- Return consistent JSON strings

Business logic remains inside app/services/.
"""

import json

from langchain_core.tools import tool

from app.services import book_service
from app.services import circulation_service
from app.services import recommendation_service
from app.services import fine_service


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _tool_response(result) -> str:
    """
    Convert service results into a valid JSON string.

    This keeps tool output predictable for the LLM.
    """

    if result is None:
        result = {
            "success": False,
            "error": "The service returned no result.",
        }

    elif isinstance(result, str):
        return result

    elif isinstance(result, list):
        result = {
            "success": True,
            "data": result,
        }

    elif not isinstance(result, dict):
        result = {
            "success": True,
            "data": str(result),
        }

    return json.dumps(result, default=str)


def _clean_student_id(student_id: str) -> str:
    """
    Normalize student ID.

    Reject placeholder values that an LLM might generate.
    """

    if not isinstance(student_id, str):
        return ""

    student_id = student_id.strip()

    if student_id.lower() in {
        "current_user",
        "current_student",
        "authenticated_user",
        "authenticated_student",
        "user",
        "student",
    }:
        return ""

    return student_id


def _validate_book_id(book_id: str) -> str:
    """Normalize and validate book ID."""

    if not isinstance(book_id, str):
        return ""

    return book_id.strip()


# ============================================================
# SEARCH CATALOG
# ============================================================

@tool
def search_catalog(
    query: str,
    top_k: int = 5,
) -> str:
    """
    Search the library catalog.

    Use this for:
    - general book searches
    - topic searches
    - title searches
    - author searches
    """

    if not isinstance(query, str) or not query.strip():
        return _tool_response({
            "success": False,
            "error": "Search query cannot be empty.",
        })

    try:
        top_k = max(
            1,
            min(int(top_k), 20),
        )
    except (TypeError, ValueError):
        top_k = 5

    try:
        result = book_service.search_books(
            query=query.strip(),
            top_k=top_k,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": f"Book search failed: {str(exc)}",
        })


# ============================================================
# BOOK AVAILABILITY
# ============================================================

@tool
def check_book_availability(
    book_id: str,
) -> str:
    """
    Check live availability of a specific book.

    Requires the actual book_id.
    """

    book_id = _validate_book_id(book_id)

    if not book_id:
        return _tool_response({
            "success": False,
            "error": "A valid book_id is required.",
        })

    try:

        book = book_service.get_book_by_id(
            book_id
        )

        if not book:
            return _tool_response({
                "success": False,
                "error": (
                    f"Book {book_id} was not found."
                ),
            })

        availability = book_service.get_availability(
            book_id
        )

        if not availability:
            return _tool_response({
                "success": False,
                "error": (
                    f"Availability for {book_id} "
                    "could not be determined."
                ),
            })

        available_copies = availability.get(
            "available_copies",
            0,
        )

        return _tool_response({
            "success": True,
            "book_id": book.get(
                "book_id",
                book_id,
            ),
            "title": book.get("title"),
            "author": book.get("author"),
            "total_copies": availability.get(
                "total_copies",
                0,
            ),
            "available_copies": available_copies,
            "available": (
                available_copies > 0
            ),
            "shelf_location": availability.get(
                "shelf_location"
            ),
        })

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Availability check failed: {str(exc)}"
            ),
        })


# ============================================================
# MOOD-BASED RECOMMENDATIONS
# ============================================================

@tool
def recommend_books_by_mood(
    mood: str,
    intent: str = "",
    difficulty: str = "",
    top_k: int = 5,
) -> str:
    """
    Recommend books based on the student's reading mood
    or preference.

    Mood examples:
        happy
        stressed
        relaxed
        curious
        bored
        motivated
        focused

    Intent examples:
        uplifting
        relaxing
        exploratory
        interesting
        learning
        challenging
    """

    if not isinstance(mood, str) or not mood.strip():
        return _tool_response({
            "success": False,
            "error": "Mood is required.",
        })

    if not isinstance(intent, str):
        intent = ""

    if not isinstance(difficulty, str):
        difficulty = ""

    try:
        top_k = max(
            1,
            min(int(top_k), 10),
        )
    except (TypeError, ValueError):
        top_k = 5

    try:

        result = (
            recommendation_service
            .recommend_by_mood(
                mood=mood.strip(),
                intent=intent.strip(),
                difficulty=difficulty.strip(),
                top_k=top_k,
            )
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                "Mood recommendation failed: "
                f"{str(exc)}"
            ),
        })


# ============================================================
# GOAL-BASED RECOMMENDATIONS
# ============================================================

@tool
def recommend_books_for_goal(
    goal: str,
    current_skills: str = "",
    topics: str = "",
    top_k: int = 5,
) -> str:
    """
    Recommend library books based on a learning,
    academic, or career goal.
    """

    if not isinstance(goal, str) or not goal.strip():
        return _tool_response({
            "success": False,
            "error": (
                "Learning or career goal is required."
            ),
        })

    if not isinstance(current_skills, str):
        current_skills = ""

    if not isinstance(topics, str):
        topics = ""

    try:
        top_k = max(
            1,
            min(int(top_k), 10),
        )
    except (TypeError, ValueError):
        top_k = 5

    try:

        result = (
            recommendation_service
            .recommend_for_goal(
                goal=goal.strip(),
                current_skills=current_skills.strip(),
                topics=topics.strip(),
                top_k=top_k,
            )
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                "Goal recommendation failed: "
                f"{str(exc)}"
            ),
        })


# ============================================================
# COURSE-BASED RECOMMENDATIONS
# ============================================================

@tool
def recommend_books_for_course(
    course_code: str,
    weak_topic: str = "",
    top_k: int = 5,
) -> str:
    """
    Recommend books for a specific course.

    weak_topic is optional.
    """

    if (
        not isinstance(course_code, str)
        or not course_code.strip()
    ):
        return _tool_response({
            "success": False,
            "error": "course_code is required.",
        })

    if not isinstance(weak_topic, str):
        weak_topic = ""

    try:
        top_k = max(
            1,
            min(int(top_k), 10),
        )
    except (TypeError, ValueError):
        top_k = 5

    try:

        result = (
            recommendation_service
            .recommend_for_course(
                course_code=course_code.strip(),
                weak_topic=weak_topic.strip(),
                top_k=top_k,
            )
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                "Course recommendation failed: "
                f"{str(exc)}"
            ),
        })


# ============================================================
# BORROW BOOK
# ============================================================

@tool
def borrow_book(
    book_id: str,
    student_id: str,
) -> str:
    """
    Borrow a book for the authenticated student.
    """

    book_id = _validate_book_id(book_id)
    student_id = _clean_student_id(student_id)

    if not book_id:
        return _tool_response({
            "success": False,
            "error": "A valid book_id is required.",
        })

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        result = circulation_service.issue_book(
            book_id=book_id,
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Borrow operation failed: {str(exc)}"
            ),
        })


# ============================================================
# RETURN BOOK
# ============================================================

@tool
def return_book(
    book_id: str,
    student_id: str,
) -> str:
    """
    Return a book borrowed by the authenticated student.
    """

    book_id = _validate_book_id(book_id)
    student_id = _clean_student_id(student_id)

    if not book_id:
        return _tool_response({
            "success": False,
            "error": "A valid book_id is required.",
        })

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        result = circulation_service.return_book(
            book_id=book_id,
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Return operation failed: {str(exc)}"
            ),
        })


# ============================================================
# RENEW BOOK
# ============================================================

@tool
def renew_book(
    book_id: str,
    student_id: str,
) -> str:
    """
    Renew a book borrowed by the authenticated student.
    """

    book_id = _validate_book_id(book_id)
    student_id = _clean_student_id(student_id)

    if not book_id:
        return _tool_response({
            "success": False,
            "error": "A valid book_id is required.",
        })

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        result = circulation_service.renew_book(
            book_id=book_id,
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Renew operation failed: {str(exc)}"
            ),
        })


# ============================================================
# RESERVE BOOK
# ============================================================

@tool
def reserve_book(
    book_id: str,
    student_id: str,
) -> str:
    """
    Reserve a book for the authenticated student.
    """

    book_id = _validate_book_id(book_id)
    student_id = _clean_student_id(student_id)

    if not book_id:
        return _tool_response({
            "success": False,
            "error": "A valid book_id is required.",
        })

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        result = circulation_service.reserve_book(
            book_id=book_id,
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Reservation failed: {str(exc)}"
            ),
        })


# ============================================================
# CANCEL RESERVATION
# ============================================================

@tool
def cancel_reservation(
    book_id: str,
    student_id: str,
) -> str:
    """
    Cancel a reservation belonging to the
    authenticated student.
    """

    book_id = _validate_book_id(book_id)
    student_id = _clean_student_id(student_id)

    if not book_id:
        return _tool_response({
            "success": False,
            "error": "A valid book_id is required.",
        })

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        result = (
            circulation_service
            .cancel_reservation(
                book_id=book_id,
                student_id=student_id,
            )
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                "Cancellation failed: "
                f"{str(exc)}"
            ),
        })


# ============================================================
# STUDENT BORROWINGS
# ============================================================

@tool
def get_student_borrowings(
    student_id: str,
) -> str:
    """
    Get the authenticated student's current borrowings.
    """

    student_id = _clean_student_id(student_id)

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        # Preferred service function
        if hasattr(
            circulation_service,
            "get_student_borrowings",
        ):

            result = (
                circulation_service
                .get_student_borrowings(
                    student_id
                )
            )

        elif hasattr(
            circulation_service,
            "get_borrowed_books",
        ):

            result = (
                circulation_service
                .get_borrowed_books(
                    student_id
                )
            )

        elif hasattr(
            circulation_service,
            "get_active_borrowings",
        ):

            result = (
                circulation_service
                .get_active_borrowings(
                    student_id
                )
            )

        else:

            return _tool_response({
                "success": False,
                "error": (
                    "Borrowing lookup service "
                    "is unavailable."
                ),
            })

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                "Borrowing lookup failed: "
                f"{str(exc)}"
            ),
        })


# ============================================================
# STUDENT FINES
# ============================================================

@tool
def get_student_fines(
    student_id: str,
) -> str:
    """
    Get the authenticated student's outstanding fine.

    Uses fine_service directly because fine calculation
    and balance management belong to fine_service.
    """

    student_id = _clean_student_id(student_id)

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        balance = (
            fine_service
            .get_outstanding_fine(
                student_id
            )
        )

        return _tool_response({
            "success": True,
            "student_id": student_id,
            "outstanding_fine": round(
                float(balance),
                2,
            ),
            "has_fine": balance > 0,
        })

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                "Fine lookup failed: "
                f"{str(exc)}"
            ),
        })


# ============================================================
# PAY FINE
# ============================================================

@tool
def pay_fine(
    amount: float,
    student_id: str,
) -> str:
    """
    Pay part or all of the authenticated student's
    outstanding fine.

    The amount must not exceed the outstanding balance.
    """

    student_id = _clean_student_id(student_id)

    if not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "Authenticated student ID is required."
            ),
        })

    try:

        amount = float(amount)

    except (TypeError, ValueError):

        return _tool_response({
            "success": False,
            "error": (
                "Payment amount must be numeric."
            ),
        })

    if amount <= 0:
        return _tool_response({
            "success": False,
            "error": (
                "Payment amount must be greater "
                "than zero."
            ),
        })

    try:

        result = fine_service.pay_fine(
            student_id=student_id,
            amount=amount,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Fine payment failed: {str(exc)}"
            ),
        })


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS = [

    # --------------------------------------------------------
    # Catalog
    # --------------------------------------------------------

    search_catalog,
    check_book_availability,

    # --------------------------------------------------------
    # Recommendations
    # --------------------------------------------------------

    recommend_books_by_mood,
    recommend_books_for_goal,
    recommend_books_for_course,

    # --------------------------------------------------------
    # Circulation
    # --------------------------------------------------------

    borrow_book,
    return_book,
    renew_book,
    reserve_book,
    cancel_reservation,

    # --------------------------------------------------------
    # Student information
    # --------------------------------------------------------

    get_student_borrowings,
    get_student_fines,

    # --------------------------------------------------------
    # Fine payment
    # --------------------------------------------------------

    pay_fine,
]
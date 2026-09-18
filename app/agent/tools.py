"""
app/agent/tools.py

MindSync LangGraph tools.

Business logic remains inside app/services/.
All tool results are returned as JSON strings.
"""

import json

from langchain_core.tools import tool

from app.services import book_service
from app.services import circulation_service
from app.services import recommendation_service


# ============================================================
# HELPER
# ============================================================

def _tool_response(result) -> str:
    """Convert service results into valid JSON string content."""

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

    Reject common placeholders that the LLM may generate.
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
    }:
        return ""

    return student_id


# ============================================================
# SEARCH CATALOG
# ============================================================

@tool
def search_catalog(
    query: str,
    top_k: int = 5,
) -> str:
    """
    Search the library catalog using semantic search.

    Use this for normal book/topic searches.
    """

    if not isinstance(query, str) or not query.strip():
        return _tool_response({
            "success": False,
            "error": "Search query cannot be empty.",
        })

    try:
        top_k = max(1, min(int(top_k), 20))
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
    """Check the live availability of a book."""

    if not isinstance(book_id, str) or not book_id.strip():
        return _tool_response({
            "success": False,
            "error": "A valid book_id is required.",
        })

    book_id = book_id.strip()

    try:

        book = book_service.get_book_by_id(book_id)

        if not book:
            return _tool_response({
                "success": False,
                "error": f"Book {book_id} was not found.",
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
            "available_copies": availability.get(
                "available_copies",
                0,
            ),
            "shelf_location": availability.get(
                "shelf_location",
            ),
        })

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": str(exc),
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
    Recommend books from the library based on the student's
    expressed mood and reading preference.

    Examples:

    mood:
        stressed
        relaxed
        curious
        bored
        motivated
        focused

    intent:
        relaxing
        learn something new
        improve skills
        explore a topic
        interesting reading

    difficulty:
        beginner
        intermediate
        advanced
    """

    if not isinstance(mood, str) or not mood.strip():
        return _tool_response({
            "success": False,
            "error": "Mood is required.",
        })

    mood = mood.strip()

    if not isinstance(intent, str):
        intent = ""

    if not isinstance(difficulty, str):
        difficulty = ""

    try:
        top_k = max(1, min(int(top_k), 10))
    except (TypeError, ValueError):
        top_k = 5

    try:
        result = recommendation_service.recommend_by_mood(
            mood=mood,
            intent=intent.strip(),
            difficulty=difficulty.strip(),
            top_k=top_k,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Mood recommendation failed: {str(exc)}"
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
    Recommend library books based on a student's learning
    or career goal.

    Examples:

    goal:
        become a data scientist
        learn machine learning
        prepare for software engineering
        learn cybersecurity

    current_skills:
        beginner Python
        basic programming
        intermediate SQL

    topics:
        machine learning
        statistics
        databases
    """

    if not isinstance(goal, str) or not goal.strip():
        return _tool_response({
            "success": False,
            "error": "Learning or career goal is required.",
        })

    if not isinstance(current_skills, str):
        current_skills = ""

    if not isinstance(topics, str):
        topics = ""

    try:
        top_k = max(1, min(int(top_k), 10))
    except (TypeError, ValueError):
        top_k = 5

    try:
        result = recommendation_service.recommend_for_goal(
            goal=goal.strip(),
            current_skills=current_skills.strip(),
            topics=topics.strip(),
            top_k=top_k,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Goal recommendation failed: {str(exc)}"
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
    Recommend books for a particular course.

    Optionally provide a topic the student is weak in.

    Examples:

        course_code = CS501

        course_code = CS301
        weak_topic = SQL

        course_code = CS601
        weak_topic = machine learning
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
        top_k = max(1, min(int(top_k), 10))
    except (TypeError, ValueError):
        top_k = 5

    try:
        result = recommendation_service.recommend_for_course(
            course_code=course_code.strip(),
            weak_topic=weak_topic.strip(),
            top_k=top_k,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": (
                f"Course recommendation failed: {str(exc)}"
            ),
        })


# ============================================================
# BORROW
# ============================================================

@tool
def borrow_book(
    book_id: str,
    student_id: str,
) -> str:
    """Borrow a book for the authenticated student."""

    student_id = _clean_student_id(student_id)

    if not book_id or not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "A valid book_id and authenticated "
                "student_id are required."
            ),
        })

    try:

        result = circulation_service.issue_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": str(exc),
        })


# ============================================================
# RETURN
# ============================================================

@tool
def return_book(
    book_id: str,
    student_id: str,
) -> str:
    """Return a book borrowed by the authenticated student."""

    student_id = _clean_student_id(student_id)

    if not book_id or not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "A valid book_id and authenticated "
                "student_id are required."
            ),
        })

    try:

        result = circulation_service.return_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": str(exc),
        })


# ============================================================
# RENEW
# ============================================================

@tool
def renew_book(
    book_id: str,
    student_id: str,
) -> str:
    """Renew a book borrowed by the authenticated student."""

    student_id = _clean_student_id(student_id)

    if not book_id or not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "A valid book_id and authenticated "
                "student_id are required."
            ),
        })

    try:

        result = circulation_service.renew_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": str(exc),
        })


# ============================================================
# RESERVE
# ============================================================

@tool
def reserve_book(
    book_id: str,
    student_id: str,
) -> str:
    """Reserve an unavailable book."""

    student_id = _clean_student_id(student_id)

    if not book_id or not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "A valid book_id and authenticated "
                "student_id are required."
            ),
        })

    try:

        result = circulation_service.reserve_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": str(exc),
        })


# ============================================================
# CANCEL RESERVATION
# ============================================================

@tool
def cancel_reservation(
    book_id: str,
    student_id: str,
) -> str:
    """Cancel a student's reservation."""

    student_id = _clean_student_id(student_id)

    if not book_id or not student_id:
        return _tool_response({
            "success": False,
            "error": (
                "A valid book_id and authenticated "
                "student_id are required."
            ),
        })

    try:

        result = circulation_service.cancel_reservation(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return _tool_response(result)

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": str(exc),
        })


# ============================================================
# STUDENT BORROWINGS
# ============================================================

@tool
def get_student_borrowings(
    student_id: str,
) -> str:
    """Get books currently borrowed by the student."""

    student_id = _clean_student_id(student_id)

    if not student_id:
        return _tool_response({
            "success": False,
            "error": "Authenticated student ID is required.",
        })

    try:

        if hasattr(
            circulation_service,
            "get_student_borrowings",
        ):

            result = (
                circulation_service
                .get_student_borrowings(student_id)
            )

        elif hasattr(
            circulation_service,
            "get_borrowed_books",
        ):

            result = (
                circulation_service
                .get_borrowed_books(student_id)
            )

        elif hasattr(
            circulation_service,
            "get_active_borrowings",
        ):

            result = (
                circulation_service
                .get_active_borrowings(student_id)
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
            "error": str(exc),
        })


# ============================================================
# STUDENT FINES
# ============================================================

@tool
def get_student_fines(
    student_id: str,
) -> str:
    """Get outstanding fines for the authenticated student."""

    student_id = _clean_student_id(student_id)

    if not student_id:
        return _tool_response({
            "success": False,
            "error": "Authenticated student ID is required.",
        })

    try:

        if hasattr(
            circulation_service,
            "get_student_fines",
        ):

            result = circulation_service.get_student_fines(
                student_id
            )

            return _tool_response(result)

        if hasattr(
            circulation_service,
            "get_fines",
        ):

            result = circulation_service.get_fines(
                student_id
            )

            return _tool_response(result)

        return _tool_response({
            "success": False,
            "error": "Fine lookup service is unavailable.",
        })

    except Exception as exc:
        return _tool_response({
            "success": False,
            "error": str(exc),
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
]
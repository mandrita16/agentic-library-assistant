"""
app/agent/tools.py
------------------

LangChain tools exposed to the MindSync LangGraph agent.

Architecture:

    Groq / LangGraph
            ↓
        LangChain Tools
            ↓
    ┌───────┴────────┐
    ↓                ↓
book_service   recommendation_service
    ↓                ↓
MongoDB       ChromaDB + MongoDB

Student-specific operations obtain student_id from the
authenticated LangGraph runtime context.

The LLM does NOT provide student_id.
"""

from langchain_core.tools import tool
from langchain.tools import ToolRuntime

from app.services import (
    book_service,
    circulation_service,
    student_service,
    recommendation_service,
)


# ============================================================
# CATALOG / SEARCH TOOLS
# ============================================================


@tool
def search_catalog(
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Search the library catalog using semantic/vector search.

    Use this when the student wants to find books based on:

    - topic
    - subject
    - title
    - author
    - concept
    - general description
    """

    try:
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Search query is required.",
            }

        results = book_service.search_books(
            query=query.strip(),
            top_k=top_k,
        )

        return {
            "success": True,
            "query": query,
            "results": results,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def check_availability(
    book_id: str,
) -> dict:
    """
    Check the current live availability of a specific book.

    Availability comes from MongoDB, not semantic search.
    """

    try:
        if not book_id or not book_id.strip():
            return {
                "success": False,
                "error": "book_id is required.",
            }

        result = book_service.get_book_availability(
            book_id.strip()
        )

        if result is None:
            return {
                "success": False,
                "book_id": book_id,
                "error": "Book not found.",
            }

        return {
            "success": True,
            "book_id": book_id,
            "availability": result,
        }

    except Exception as exc:
        return {
            "success": False,
            "book_id": book_id,
            "error": str(exc),
        }


# ============================================================
# RECOMMENDATION TOOLS
# ============================================================


@tool
def find_best_available_book(
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Find the most relevant book that is currently available.

    This is a multi-step operation:

    1. Semantic retrieval from ChromaDB.
    2. Live availability lookup from MongoDB.
    3. Select the most relevant available candidate.
    4. Fall back to the best matching unavailable book if
       no candidate is currently available.
    """

    try:
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Search query is required.",
            }

        result = recommendation_service.find_best_available_book(
            query=query.strip(),
            top_k=top_k,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def recommend_for_course(
    course_code: str,
    weak_topic: str = "",
    top_k: int = 3,
) -> dict:
    """
    Recommend books for a particular course.

    Optionally use weak_topic to focus recommendations
    on an area the student finds difficult.

    The recommendation service combines semantic retrieval
    with live availability information.
    """

    try:
        if not course_code or not course_code.strip():
            return {
                "success": False,
                "error": "course_code is required.",
            }

        result = recommendation_service.recommend_for_course(
            course_code=course_code.strip(),
            weak_topic=weak_topic.strip() if weak_topic else "",
            top_k=top_k,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def recommend_for_goal(
    goal: str,
    current_skills: str = "",
    topics: str = "",
    top_k: int = 5,
) -> dict:
    """
    Recommend books based on a student's learning or
    career goal.
    """

    try:
        if not goal or not goal.strip():
            return {
                "success": False,
                "error": "goal is required.",
            }

        result = recommendation_service.recommend_for_goal(
            goal=goal.strip(),
            current_skills=(
                current_skills.strip()
                if current_skills
                else ""
            ),
            topics=topics.strip() if topics else "",
            top_k=top_k,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def recommend_by_mood(
    mood: str,
    intent: str = "",
    difficulty: str = "",
    top_k: int = 5,
) -> dict:
    """
    Recommend books based on the student's mood,
    reading intent, and optionally desired difficulty.
    """

    try:
        if not mood or not mood.strip():
            return {
                "success": False,
                "error": "mood is required.",
            }

        result = recommendation_service.recommend_by_mood(
            mood=mood.strip(),
            intent=intent.strip() if intent else "",
            difficulty=(
                difficulty.strip()
                if difficulty
                else ""
            ),
            top_k=top_k,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# PERSONALIZED STUDENT TOOLS
# ============================================================

"""
IMPORTANT SECURITY RULE:

The student's identity comes from the authenticated JWT.

The LLM does NOT provide student_id.

The flow is:

JWT
 ↓
FastAPI
 ↓
LangGraph runtime context
 ↓
ToolRuntime
 ↓
runtime.context.student_id
"""



@tool
def get_due_soon_books(
    days: int = 3,
    runtime: ToolRuntime = None,
) -> dict:
    """
    Get books belonging to the authenticated student
    that are due within the specified number of days.
    """

    try:
        if runtime is None or runtime.context is None:
            return {
                "success": False,
                "error": "Authenticated student context is missing.",
            }

        student_id = runtime.context.student_id

        results = circulation_service.get_due_soon_books(
            student_id=student_id,
            days=days,
        )

        return {
            "success": True,
            "days": days,
            "books": results,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def get_student_dashboard(
    runtime: ToolRuntime = None,
) -> dict:
    """
    Get the complete library dashboard for the
    authenticated student.

    Includes:

    - currently issued books
    - due dates
    - overdue books
    - reservations
    - fines
    - borrowing information
    """

    try:
        if runtime is None or runtime.context is None:
            return {
                "success": False,
                "error": "Authenticated student context is missing.",
            }

        student_id = runtime.context.student_id

        result = student_service.get_dashboard(
            student_id
        )

        return {
            "success": True,
            "dashboard": result,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# CIRCULATION TOOLS
# ============================================================


@tool
def issue_book(
    book_id: str,
    runtime: ToolRuntime = None,
) -> dict:
    """
    Issue a book to the authenticated student.

    The student_id is obtained securely from the
    authenticated application context.
    """

    try:
        if runtime is None or runtime.context is None:
            return {
                "success": False,
                "error": "Authenticated student context is missing.",
            }

        if not book_id or not book_id.strip():
            return {
                "success": False,
                "error": "book_id is required.",
            }

        student_id = runtime.context.student_id

        result = circulation_service.issue_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def return_book(
    book_id: str,
    runtime: ToolRuntime = None,
) -> dict:
    """
    Return a book currently issued to the
    authenticated student.
    """

    try:
        if runtime is None or runtime.context is None:
            return {
                "success": False,
                "error": "Authenticated student context is missing.",
            }

        if not book_id or not book_id.strip():
            return {
                "success": False,
                "error": "book_id is required.",
            }

        student_id = runtime.context.student_id

        result = circulation_service.return_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def renew_book(
    book_id: str,
    runtime: ToolRuntime = None,
) -> dict:
    """
    Renew a book currently issued to the
    authenticated student.
    """

    try:
        if runtime is None or runtime.context is None:
            return {
                "success": False,
                "error": "Authenticated student context is missing.",
            }

        if not book_id or not book_id.strip():
            return {
                "success": False,
                "error": "book_id is required.",
            }

        student_id = runtime.context.student_id

        result = circulation_service.renew_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def reserve_book(
    book_id: str,
    runtime: ToolRuntime = None,
) -> dict:
    """
    Reserve a currently unavailable book for the
    authenticated student.
    """

    try:
        if runtime is None or runtime.context is None:
            return {
                "success": False,
                "error": "Authenticated student context is missing.",
            }

        if not book_id or not book_id.strip():
            return {
                "success": False,
                "error": "book_id is required.",
            }

        student_id = runtime.context.student_id

        result = circulation_service.reserve_book(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


@tool
def cancel_reservation(
    book_id: str,
    runtime: ToolRuntime = None,
) -> dict:
    """
    Cancel a reservation made by the
    authenticated student.
    """

    try:
        if runtime is None or runtime.context is None:
            return {
                "success": False,
                "error": "Authenticated student context is missing.",
            }

        if not book_id or not book_id.strip():
            return {
                "success": False,
                "error": "book_id is required.",
            }

        student_id = runtime.context.student_id

        result = circulation_service.cancel_reservation(
            book_id=book_id.strip(),
            student_id=student_id,
        )

        return result

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# TOOL REGISTRY
# ============================================================


TOOLS = [
    # Catalog
    search_catalog,
    check_availability,

    # Recommendations
    find_best_available_book,
    recommend_for_course,
    recommend_for_goal,
    recommend_by_mood,

    # Student
    get_due_soon_books,
    get_student_dashboard,

    # Circulation
    issue_book,
    return_book,
    renew_book,
    reserve_book,
    cancel_reservation,
]
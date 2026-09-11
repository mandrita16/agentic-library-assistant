"""
agent/tools.py
--------------
LangChain tools used by the MindSync agent.

The tools connect the LangGraph/LLM layer to the existing
library services, RAG pipeline and database operations.

The tools contain very little business logic.
Actual business rules remain inside app.services.
"""

from datetime import datetime, timedelta

from langchain_core.tools import tool

from app.rag.vector_store import semantic_search
from app.services.book_service import get_availability
from app.services import (
    circulation_service,
    recommendation_service,
    student_service,
)


# ================================================================
# LIBRARY DISCOVERY
# ================================================================


@tool
def search_catalog(query: str, top_k: int = 5) -> dict:
    """
    Search the library catalog using semantic search.

    Use this for general questions such as finding books
    about machine learning, operating systems, databases,
    programming, etc.

    This tool does not provide live availability.
    """
    return {
        "results": semantic_search(
            query,
            top_k
        )
    }


@tool
def check_availability(book_id: str) -> dict:
    """
    Check the current availability, copy count and shelf
    location of a specific book.
    """

    result = get_availability(book_id)

    if result is None:
        return {
            "success": False,
            "error": f"Book '{book_id}' not found."
        }

    return result


@tool
def find_best_available_book(
    query: str,
    top_k: int = 5
) -> dict:
    """
    Find the most relevant book that is currently available.

    Use this when a student wants the best available book
    for a particular topic or learning requirement.
    """

    return recommendation_service.find_best_available_book(
        query,
        top_k
    )


@tool
def recommend_for_course(
    course_code: str,
    weak_topic: str = "",
    top_k: int = 3
) -> dict:
    """
    Recommend books for a university course.

    Optionally consider a topic that the student is
    struggling with.
    """

    return recommendation_service.recommend_for_course(
        course_code,
        weak_topic or None,
        top_k
    )


@tool
def recommend_for_goal(
    goal: str,
    current_skills: str = "",
    topics: str = "",
    top_k: int = 5
) -> dict:
    """
    Recommend library books based on a student's academic,
    career, examination or learning goal.
    """

    query_parts = [goal]

    if current_skills:
        query_parts.append(current_skills)

    if topics:
        query_parts.append(topics)

    query = " ".join(query_parts)

    candidates = semantic_search(
        query,
        top_k=top_k
    )

    recommendations = []

    for candidate in candidates:

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        availability = get_availability(book_id)

        if not availability:
            continue

        recommendations.append({
            "book_id": book_id,
            "title": availability.get("title"),
            "available_copies": availability.get(
                "available_copies",
                0
            ),
            "shelf_location": availability.get(
                "shelf_location"
            ),
            "relevance": candidate.get("distance"),
        })

    return {
        "goal": goal,
        "current_skills": current_skills,
        "topics": topics,
        "recommendations": recommendations,
    }


@tool
def recommend_by_mood(
    mood: str,
    intent: str = "",
    difficulty: str = "",
    top_k: int = 5
) -> dict:
    """
    Recommend books based on mood, reading intention
    or difficulty preference.

    This is a reading-preference feature and not a
    medical or psychological diagnosis.
    """

    query_parts = [mood]

    if intent:
        query_parts.append(intent)

    if difficulty:
        query_parts.append(difficulty)

    query = " ".join(query_parts)

    candidates = semantic_search(
        query,
        top_k=top_k
    )

    recommendations = []

    for candidate in candidates:

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        availability = get_availability(book_id)

        if not availability:
            continue

        recommendations.append({
            "book_id": book_id,
            "title": availability.get("title"),
            "available_copies": availability.get(
                "available_copies",
                0
            ),
            "shelf_location": availability.get(
                "shelf_location"
            ),
            "relevance": candidate.get("distance"),
        })

    return {
        "mood": mood,
        "intent": intent,
        "difficulty": difficulty,
        "recommendations": recommendations,
    }


# ================================================================
# STUDENT ASSISTANCE
# ================================================================


@tool
def get_due_soon_books(
    student_id: str,
    days: int = 3
) -> dict:
    """
    Find books that are overdue or due within a specified
    number of days.
    """

    days = max(0, min(days, 30))

    dashboard = student_service.get_dashboard(
        student_id
    )

    borrowed_books = dashboard.get(
        "borrowed_details",
        []
    )

    now = datetime.utcnow()
    deadline = now + timedelta(days=days)

    due_soon = []

    for record in borrowed_books:

        due_date = record.get("due_date")

        if not due_date:
            continue

        if isinstance(due_date, str):

            try:
                due_date = datetime.fromisoformat(
                    due_date.replace("Z", "+00:00")
                )

                if due_date.tzinfo is not None:
                    due_date = due_date.replace(
                        tzinfo=None
                    )

            except ValueError:
                continue

        is_overdue = due_date < now
        is_due_soon = now <= due_date <= deadline

        if is_overdue or is_due_soon:

            days_remaining = (
                due_date.date() - now.date()
            ).days

            due_soon.append({
                "book_id": record.get("book_id"),
                "due_date": due_date.isoformat(),
                "days_remaining": days_remaining,
                "status": (
                    "overdue"
                    if is_overdue
                    else "due_soon"
                ),
                "current_overdue_fine": record.get(
                    "current_overdue_fine",
                    0
                ),
            })

    return {
        "student_id": student_id,
        "days_checked": days,
        "books_due_soon": due_soon,
        "count": len(due_soon),
    }


@tool
def get_student_dashboard(
    student_id: str
) -> dict:
    """
    Get a student's complete library account information,
    including borrowed books, due information, reservations
    and outstanding fines.
    """

    return student_service.get_dashboard(
        student_id
    )


# ================================================================
# CIRCULATION
# ================================================================


@tool
def issue_book(
    book_id: str,
    student_id: str
) -> dict:
    """
    Issue a book to a student if a copy is available.
    """

    return circulation_service.issue_book(
        book_id,
        student_id
    )


@tool
def return_book(
    book_id: str,
    student_id: str
) -> dict:
    """
    Return a borrowed book and calculate any applicable fine.
    """

    return circulation_service.return_book(
        book_id,
        student_id
    )


@tool
def renew_book(
    book_id: str,
    student_id: str
) -> dict:
    """
    Renew a borrowed book if renewal rules allow it.
    """

    return circulation_service.renew_book(
        book_id,
        student_id
    )


@tool
def reserve_book(
    book_id: str,
    student_id: str
) -> dict:
    """
    Reserve a book when no copies are currently available.
    """

    return circulation_service.reserve_book(
        book_id,
        student_id
    )


@tool
def cancel_reservation(
    book_id: str,
    student_id: str
) -> dict:
    """
    Cancel an active reservation or waitlist entry.
    """

    return circulation_service.cancel_reservation(
        book_id,
        student_id
    )


# ================================================================
# TOOL COLLECTION
# ================================================================


TOOLS = [
    search_catalog,
    check_availability,
    find_best_available_book,
    recommend_for_course,
    recommend_for_goal,
    recommend_by_mood,
    get_due_soon_books,
    get_student_dashboard,
    issue_book,
    return_book,
    renew_book,
    reserve_book,
    cancel_reservation,
]
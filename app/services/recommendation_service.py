"""
services/recommendation_service.py
-----------------------------------

Compound recommendation logic for MindSync.

This service is different from book_service.py:

book_service.py
    → catalog access and semantic retrieval

recommendation_service.py
    → combines retrieval + live data + decision-making

This is one of the main places where MindSync demonstrates
agentic behavior.
"""

from app.rag.vector_store import semantic_search
from app.services.book_service import (
    get_book_by_id,
    get_availability,
)


# ============================================================
# BEST AVAILABLE BOOK
# ============================================================


def find_best_available_book(
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Find the most relevant book that is currently available.

    Pipeline:

        Natural-language query
                ↓
        Semantic retrieval
                ↓
        Candidate books
                ↓
        Live MongoDB availability check
                ↓
        Select first available candidate

    If none of the candidates are available, return the most
    relevant book with a clear unavailable status.
    """

    if not query or not query.strip():
        return {
            "success": False,
            "found": False,
            "message": "Search query is required.",
        }

    top_k = max(1, min(top_k, 20))

    candidates = semantic_search(
        query=query.strip(),
        top_k=top_k,
    )

    if not candidates:
        return {
            "success": True,
            "found": False,
            "message": "No matching books found in the catalog.",
        }

    # --------------------------------------------------------
    # Check candidates in semantic relevance order.
    # --------------------------------------------------------

    for candidate in candidates:

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        availability = get_availability(book_id)

        if not availability:
            continue

        if availability.get("available_copies", 0) > 0:

            return {
                "success": True,
                "found": True,
                "available_now": True,
                "book_id": book_id,
                "title": availability.get("title"),
                "available_copies": availability.get(
                    "available_copies",
                    0,
                ),
                "total_copies": availability.get(
                    "total_copies",
                    0,
                ),
                "shelf_location": availability.get(
                    "shelf_location",
                ),
            }

    # --------------------------------------------------------
    # Nothing available.
    #
    # Return the most relevant valid catalog book.
    # --------------------------------------------------------

    for candidate in candidates:

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        book = get_book_by_id(book_id)

        if not book:
            continue

        availability = get_availability(book_id)

        return {
            "success": True,
            "found": True,
            "available_now": False,
            "book_id": book_id,
            "title": book.get("title"),
            "available_copies": (
                availability.get("available_copies", 0)
                if availability
                else 0
            ),
            "shelf_location": (
                availability.get("shelf_location")
                if availability
                else book.get("shelf_location")
            ),
            "message": (
                "Best matching book found, but no copies "
                "are currently available. Consider reserving it."
            ),
        }

    return {
        "success": True,
        "found": False,
        "message": (
            "Matching books were found in semantic search, "
            "but their catalog records are no longer available."
        ),
    }


# ============================================================
# COURSE RECOMMENDATIONS
# ============================================================


def recommend_for_course(
    course_code: str,
    weak_topic: str | None = None,
    top_k: int = 3,
) -> dict:
    """
    Recommend books for a course and optional weak topic.

    Pipeline:

        Course + weak topic
                ↓
        Semantic retrieval
                ↓
        Live availability lookup
                ↓
        Ranked shortlist
    """

    if not course_code or not course_code.strip():
        return {
            "success": False,
            "message": "course_code is required.",
        }

    course_code = course_code.strip()

    query_parts = [course_code]

    if weak_topic and weak_topic.strip():
        query_parts.append(weak_topic.strip())

    query = " ".join(query_parts)

    top_k = max(1, min(top_k, 20))

    candidates = semantic_search(
        query=query,
        top_k=top_k,
    )

    recommendations = []

    for candidate in candidates:

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        book = get_book_by_id(book_id)

        if not book:
            continue

        availability = get_availability(book_id)

        recommendations.append(
            {
                "book_id": book_id,
                "title": book.get("title"),
                "author": book.get("author"),
                "subject": book.get("subject"),
                "available_copies": (
                    availability.get(
                        "available_copies",
                        0,
                    )
                    if availability
                    else 0
                ),
                "total_copies": (
                    availability.get(
                        "total_copies",
                        0,
                    )
                    if availability
                    else 0
                ),
                "shelf_location": (
                    availability.get(
                        "shelf_location"
                    )
                    if availability
                    else book.get("shelf_location")
                ),
            }
        )

    return {
        "success": True,
        "course_code": course_code,
        "weak_topic": weak_topic or "",
        "recommendations": recommendations,
    }


# ============================================================
# GOAL-BASED RECOMMENDATIONS
# ============================================================


def recommend_for_goal(
    goal: str,
    current_skills: str = "",
    topics: str = "",
    top_k: int = 5,
) -> dict:
    """
    Recommend books for a student's learning or career goal.

    The goal, current skills, and desired topics are combined
    into a semantic retrieval query.
    """

    if not goal or not goal.strip():
        return {
            "success": False,
            "message": "goal is required.",
        }

    query_parts = [
        goal.strip(),
    ]

    if current_skills and current_skills.strip():
        query_parts.append(
            f"Current skills: {current_skills.strip()}"
        )

    if topics and topics.strip():
        query_parts.append(
            f"Topics: {topics.strip()}"
        )

    query = " | ".join(query_parts)

    candidates = semantic_search(
        query=query,
        top_k=max(1, min(top_k, 20)),
    )

    recommendations = []

    for candidate in candidates:

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        book = get_book_by_id(book_id)

        if not book:
            continue

        availability = get_availability(book_id)

        recommendations.append(
            {
                "book_id": book_id,
                "title": book.get("title"),
                "author": book.get("author"),
                "subject": book.get("subject"),
                "available_copies": (
                    availability.get(
                        "available_copies",
                        0,
                    )
                    if availability
                    else 0
                ),
                "shelf_location": (
                    availability.get(
                        "shelf_location"
                    )
                    if availability
                    else book.get("shelf_location")
                ),
            }
        )

    return {
        "success": True,
        "goal": goal,
        "recommendations": recommendations,
    }


# ============================================================
# MOOD-BASED RECOMMENDATIONS
# ============================================================


def recommend_by_mood(
    mood: str,
    intent: str = "",
    difficulty: str = "",
    top_k: int = 5,
) -> dict:
    """
    Recommend books based on mood, reading intent,
    and optional difficulty.
    """

    if not mood or not mood.strip():
        return {
            "success": False,
            "message": "mood is required.",
        }

    query_parts = [
        mood.strip(),
    ]

    if intent and intent.strip():
        query_parts.append(
            f"Reading intent: {intent.strip()}"
        )

    if difficulty and difficulty.strip():
        query_parts.append(
            f"Difficulty: {difficulty.strip()}"
        )

    query = " | ".join(query_parts)

    candidates = semantic_search(
        query=query,
        top_k=max(1, min(top_k, 20)),
    )

    recommendations = []

    for candidate in candidates:

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        book = get_book_by_id(book_id)

        if not book:
            continue

        availability = get_availability(book_id)

        recommendations.append(
            {
                "book_id": book_id,
                "title": book.get("title"),
                "author": book.get("author"),
                "subject": book.get("subject"),
                "available_copies": (
                    availability.get(
                        "available_copies",
                        0,
                    )
                    if availability
                    else 0
                ),
                "shelf_location": (
                    availability.get(
                        "shelf_location"
                    )
                    if availability
                    else book.get("shelf_location")
                ),
            }
        )

    return {
        "success": True,
        "mood": mood,
        "intent": intent,
        "difficulty": difficulty,
        "recommendations": recommendations,
    }
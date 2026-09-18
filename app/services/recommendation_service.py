"""
services/recommendation_service.py
-----------------------------------

Compound recommendation logic for MindSync.

Responsibilities:

    - Semantic book retrieval
    - Live MongoDB availability
    - Course-based recommendations
    - Goal-based recommendations
    - Mood-based recommendations
    - Best available book selection

Important:

    This service does NOT call the LLM.

    Therefore it does not directly consume Groq tokens.

    The goal is to keep tool responses compact so that
    the agent has less data to send back to the LLM.
"""

from app.rag.vector_store import semantic_search
from app.services.book_service import get_book_by_id


# ============================================================
# CONSTANTS
# ============================================================

MAX_TOP_K = 20


def _normalize_top_k(top_k: int, default: int = 5) -> int:
    """
    Keep retrieval size within a safe range.
    """

    if not isinstance(top_k, int):
        top_k = default

    return max(
        1,
        min(top_k, MAX_TOP_K),
    )


def _compact_book(
    book: dict,
    include_total: bool = False,
) -> dict:
    """
    Convert a MongoDB book document into a compact
    tool response.

    Keeping tool output small helps reduce the amount
    of context sent back to the LLM.
    """

    result = {
        "book_id": book.get("book_id"),
        "title": book.get("title"),
        "author": book.get("author"),
        "subject": book.get("subject"),
        "available_copies": book.get(
            "available_copies",
            0,
        ),
        "shelf_location": book.get(
            "shelf_location",
        ),
    }

    if include_total:
        result["total_copies"] = book.get(
            "total_copies",
            0,
        )

    return result


def _get_candidate_books(
    candidates: list[dict],
) -> list[dict]:
    """
    Resolve Chroma candidates against MongoDB.

    MongoDB remains the source of truth.

    Each candidate results in only ONE MongoDB lookup.
    """

    books = []

    for candidate in candidates:

        if not isinstance(candidate, dict):
            continue

        book_id = candidate.get("book_id")

        if not book_id:
            continue

        book = get_book_by_id(book_id)

        if not book:
            continue

        books.append(book)

    return books


# ============================================================
# BEST AVAILABLE BOOK
# ============================================================


def find_best_available_book(
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Find the most relevant currently available book.

    Pipeline:

        Query
          ↓
        ChromaDB semantic search
          ↓
        MongoDB catalog lookup
          ↓
        Availability check
          ↓
        Best available book
    """

    if not isinstance(query, str):
        return {
            "success": False,
            "found": False,
            "message": "Search query is required.",
        }

    query = query.strip()

    if not query:
        return {
            "success": False,
            "found": False,
            "message": "Search query is required.",
        }

    top_k = _normalize_top_k(top_k)

    candidates = semantic_search(
        query=query,
        top_k=top_k,
    )

    if not candidates:
        return {
            "success": True,
            "found": False,
            "message": (
                "No matching books found in the catalog."
            ),
        }

    books = _get_candidate_books(
        candidates
    )

    if not books:
        return {
            "success": True,
            "found": False,
            "message": (
                "Matching books were found, "
                "but their catalog records are unavailable."
            ),
        }

    # --------------------------------------------------------
    # First available book
    # --------------------------------------------------------

    for book in books:

        if book.get(
            "available_copies",
            0,
        ) > 0:

            result = _compact_book(
                book,
                include_total=True,
            )

            result.update(
                {
                    "success": True,
                    "found": True,
                    "available_now": True,
                }
            )

            return result

    # --------------------------------------------------------
    # No available books.
    #
    # Return the most relevant book.
    # --------------------------------------------------------

    best_book = books[0]

    result = _compact_book(
        best_book,
        include_total=True,
    )

    result.update(
        {
            "success": True,
            "found": True,
            "available_now": False,
            "message": (
                "Best matching book found, but no copies "
                "are currently available. Consider reserving it."
            ),
        }
    )

    return result


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

    No LLM is used.
    """

    if not isinstance(course_code, str):
        return {
            "success": False,
            "message": "course_code is required.",
        }

    course_code = course_code.strip()

    if not course_code:
        return {
            "success": False,
            "message": "course_code is required.",
        }

    query_parts = [
        course_code
    ]

    if isinstance(weak_topic, str):
        weak_topic = weak_topic.strip()

        if weak_topic:
            query_parts.append(
                weak_topic
            )

    query = " ".join(
        query_parts
    )

    top_k = _normalize_top_k(
        top_k,
        default=3,
    )

    candidates = semantic_search(
        query=query,
        top_k=top_k,
    )

    books = _get_candidate_books(
        candidates
    )

    recommendations = [
        _compact_book(book)
        for book in books
    ]

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
    Recommend books for a learning or career goal.

    Semantic retrieval is performed directly against
    the vector store.

    No LLM is used.
    """

    if not isinstance(goal, str):
        return {
            "success": False,
            "message": "goal is required.",
        }

    goal = goal.strip()

    if not goal:
        return {
            "success": False,
            "message": "goal is required.",
        }

    query_parts = [
        goal
    ]

    if isinstance(current_skills, str):
        current_skills = current_skills.strip()

        if current_skills:
            query_parts.append(
                f"Current skills: {current_skills}"
            )

    if isinstance(topics, str):
        topics = topics.strip()

        if topics:
            query_parts.append(
                f"Topics: {topics}"
            )

    query = " | ".join(
        query_parts
    )

    top_k = _normalize_top_k(
        top_k
    )

    candidates = semantic_search(
        query=query,
        top_k=top_k,
    )

    books = _get_candidate_books(
        candidates
    )

    recommendations = [
        _compact_book(book)
        for book in books
    ]

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
    Recommend books based on:

        - mood
        - reading intent
        - difficulty

    No LLM is used.

    Example:

        mood = stressed
        intent = relaxing

    becomes:

        "stressed | Reading intent: relaxing"
    """

    if not isinstance(mood, str):
        return {
            "success": False,
            "message": "mood is required.",
        }

    mood = mood.strip()

    if not mood:
        return {
            "success": False,
            "message": "mood is required.",
        }

    query_parts = [
        mood
    ]

    if isinstance(intent, str):
        intent = intent.strip()

        if intent:
            query_parts.append(
                f"Reading intent: {intent}"
            )

    if isinstance(difficulty, str):
        difficulty = difficulty.strip()

        if difficulty:
            query_parts.append(
                f"Difficulty: {difficulty}"
            )

    query = " | ".join(
        query_parts
    )

    top_k = _normalize_top_k(
        top_k
    )

    candidates = semantic_search(
        query=query,
        top_k=top_k,
    )

    books = _get_candidate_books(
        candidates
    )

    recommendations = [
        _compact_book(book)
        for book in books
    ]

    return {
        "success": True,
        "mood": mood,
        "intent": intent,
        "difficulty": difficulty,
        "recommendations": recommendations,
    }
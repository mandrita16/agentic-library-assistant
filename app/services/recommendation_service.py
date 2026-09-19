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
"""

from app.rag.vector_store import semantic_search
from app.services.book_service import get_book_by_id


# ============================================================
# CONSTANTS
# ============================================================

MAX_TOP_K = 20

# Subjects that are closely related to common AI/ML goals.
RELATED_SUBJECTS = {
    "machine learning": {
        "machine learning",
        "deep learning",
        "data science",
        "artificial intelligence",
    },

    "natural language processing": {
        "natural language processing",
        "machine learning",
        "deep learning",
        "artificial intelligence",
    },

    "nlp": {
        "natural language processing",
        "machine learning",
        "deep learning",
        "artificial intelligence",
    },

    "deep learning": {
        "deep learning",
        "machine learning",
        "artificial intelligence",
        "computer vision",
    },

    "artificial intelligence": {
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "natural language processing",
        "computer vision",
    },

    "computer vision": {
        "computer vision",
        "deep learning",
        "machine learning",
        "artificial intelligence",
    },

    "data science": {
        "data science",
        "machine learning",
        "data analysis",
        "statistics",
    },
}


# ============================================================
# HELPERS
# ============================================================

def _normalize_top_k(
    top_k: int,
    default: int = 5,
) -> int:
    """
    Keep retrieval size within a safe range.
    """

    if not isinstance(top_k, int):
        top_k = default

    return max(
        1,
        min(top_k, MAX_TOP_K),
    )


def _normalize_text(value) -> str:
    """
    Normalize text for matching.
    """

    if not isinstance(value, str):
        return ""

    return (
        value
        .strip()
        .lower()
    )


def _compact_book(
    book: dict,
    include_total: bool = False,
) -> dict:
    """
    Convert a MongoDB book document into a compact
    tool response.
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
    """

    books = []

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        book_id = candidate.get(
            "book_id"
        )

        if not book_id:
            continue

        book = get_book_by_id(
            book_id
        )

        if not book:
            continue

        books.append(book)

    return books


# ============================================================
# GOAL CLASSIFICATION
# ============================================================

def _get_goal_category(
    goal: str,
) -> str:
    """
    Convert a user's goal into a normalized
    recommendation category.

    This is intentionally rule-based.

    The LLM is not used here.
    """

    goal = _normalize_text(
        goal
    )

    if (
        "natural language processing" in goal
        or goal == "nlp"
        or " nlp " in f" {goal} "
    ):
        return "natural language processing"

    if (
        "machine learning" in goal
        or goal == "ml"
        or " ml " in f" {goal} "
    ):
        return "machine learning"

    if "deep learning" in goal:
        return "deep learning"

    if (
        "computer vision" in goal
        or "image processing" in goal
    ):
        return "computer vision"

    if (
        "artificial intelligence" in goal
        or goal == "ai"
        or " ai " in f" {goal} "
    ):
        return "artificial intelligence"

    if "data science" in goal:
        return "data science"

    return goal


def _filter_goal_books(
    books: list[dict],
    goal: str,
) -> list[dict]:
    """
    Keep books relevant to the requested goal.

    Direct subject matches are always retained.

    Related subjects are retained only when the
    goal belongs to a known technical category.

    This prevents results such as:
        NLP -> Database Systems
        NLP -> Computer Architecture
        NLP -> Operating Systems
    """

    category = _get_goal_category(
        goal
    )

    allowed_subjects = RELATED_SUBJECTS.get(
        category
    )

    # --------------------------------------------------------
    # Unknown goal
    #
    # Do not aggressively filter arbitrary searches.
    # --------------------------------------------------------

    if not allowed_subjects:
        return books

    filtered = []

    for book in books:

        subject = _normalize_text(
            book.get("subject")
        )

        if subject in allowed_subjects:
            filtered.append(book)

    return filtered


def _rank_goal_books(
    books: list[dict],
    goal: str,
) -> list[dict]:
    """
    Rank books so that direct subject matches appear
    before related subjects.

    Original semantic-search order is preserved
    within each relevance group.
    """

    category = _get_goal_category(
        goal
    )

    direct_subjects = {
        category
    }

    if category == "nlp":
        direct_subjects.add(
            "natural language processing"
        )

    direct = []
    related = []

    for book in books:

        subject = _normalize_text(
            book.get("subject")
        )

        if subject in direct_subjects:
            direct.append(book)
        else:
            related.append(book)

    return direct + related


# ============================================================
# BEST AVAILABLE BOOK
# ============================================================

def find_best_available_book(
    query: str,
    top_k: int = 5,
) -> dict:
    """
    Find the most relevant currently available book.
    """

    if not isinstance(
        query,
        str,
    ):
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

    top_k = _normalize_top_k(
        top_k
    )

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
    """

    if not isinstance(
        course_code,
        str,
    ):
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

    if isinstance(
        weak_topic,
        str,
    ):
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

    Retrieval pipeline:

        User goal
            ↓
        Chroma semantic search
            ↓
        MongoDB lookup
            ↓
        Goal relevance filtering
            ↓
        Direct subject ranking
            ↓
        Final recommendations
    """

    if not isinstance(
        goal,
        str,
    ):
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

    # --------------------------------------------------------
    # Normalize optional parameters
    # --------------------------------------------------------

    if not isinstance(
        current_skills,
        str,
    ):
        current_skills = ""

    if not isinstance(
        topics,
        str,
    ):
        topics = ""

    current_skills = current_skills.strip()
    topics = topics.strip()

    # --------------------------------------------------------
    # Semantic query
    # --------------------------------------------------------

    query_parts = [
        goal
    ]

    if current_skills:
        query_parts.append(
            f"Current skills: {current_skills}"
        )

    if topics:
        query_parts.append(
            f"Topics: {topics}"
        )

    query = " | ".join(
        query_parts
    )

    # --------------------------------------------------------
    # Retrieve MORE candidates than requested.
    #
    # This is important.
    #
    # If top_k = 5 and the first 5 semantic results
    # contain unrelated books, filtering them afterward
    # could leave only one useful book.
    #
    # Therefore retrieve up to 20 candidates first.
    # --------------------------------------------------------

    requested_top_k = _normalize_top_k(
        top_k
    )

    retrieval_k = max(
        requested_top_k * 3,
        10,
    )

    retrieval_k = min(
        retrieval_k,
        MAX_TOP_K,
    )

    candidates = semantic_search(
        query=query,
        top_k=retrieval_k,
    )

    books = _get_candidate_books(
        candidates
    )

    # --------------------------------------------------------
    # Remove duplicate books
    # --------------------------------------------------------

    unique_books = []

    seen_ids = set()

    for book in books:

        book_id = book.get(
            "book_id"
        )

        if not book_id:
            continue

        if book_id in seen_ids:
            continue

        seen_ids.add(
            book_id
        )

        unique_books.append(
            book
        )

    # --------------------------------------------------------
    # Goal-specific filtering
    # --------------------------------------------------------

    filtered_books = _filter_goal_books(
        unique_books,
        goal,
    )

    # --------------------------------------------------------
    # Rank direct matches before related matches
    # --------------------------------------------------------

    ranked_books = _rank_goal_books(
        filtered_books,
        goal,
    )

    # --------------------------------------------------------
    # Final top K
    # --------------------------------------------------------

    ranked_books = ranked_books[
        :requested_top_k
    ]

    recommendations = [
        _compact_book(book)
        for book in ranked_books
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
    Recommend books based on mood,
    reading intent and difficulty.
    """

    if not isinstance(
        mood,
        str,
    ):
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

    if isinstance(
        intent,
        str,
    ):
        intent = intent.strip()

        if intent:
            query_parts.append(
                f"Reading intent: {intent}"
            )

    if isinstance(
        difficulty,
        str,
    ):
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
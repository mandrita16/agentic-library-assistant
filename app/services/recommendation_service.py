"""
services/recommendation_service.py
------------------------------------
This is the file to point to when someone asks "okay but what makes
this actually AGENTIC and not just a chatbot with search?"

Both functions here CHAIN multiple steps together — semantic retrieval,
then a live-data lookup, then ranking — and make a decision (which book
is "best") rather than just returning raw search hits. That chaining and
decision-making is what the agent's tool-calling loop invokes when a
student asks something like "give me the best available NLP book."
"""

from app.rag.vector_store import semantic_search
from app.services.book_service import get_availability


def find_best_available_book(query: str, top_k: int = 5) -> dict:
    """
    Chain: semantic search -> check live availability for each candidate
    -> filter to ones with copies free -> return the most relevant
    AVAILABLE one (falling back to the most relevant one overall if
    nothing is currently free, with a clear note about that).
    """
    candidates = semantic_search(query, top_k=top_k)
    if not candidates:
        return {"found": False, "message": "No matching books found in the catalog."}

    for candidate in candidates:  # already sorted by relevance (lowest distance first)
        availability = get_availability(candidate["book_id"])
        if availability and availability["available_copies"] > 0:
            return {
                "found": True,
                "available_now": True,
                "book_id": candidate["book_id"],
                "title": availability["title"],
                "available_copies": availability["available_copies"],
                "shelf_location": availability["shelf_location"],
            }

    # Nothing in the top candidates is currently available — surface the
    # single best match anyway, but be honest that it's not free right now.
    top = candidates[0]
    availability = get_availability(top["book_id"]) or {}
    return {
        "found": True,
        "available_now": False,
        "book_id": top["book_id"],
        "title": availability.get("title", top["metadata"].get("title")),
        "message": "Best match found, but no copies are currently available. Consider reserving it.",
    }


def recommend_for_course(course_code: str, weak_topic: str | None = None, top_k: int = 3) -> dict:
    """
    Chain: build a query from course + optional weak-topic context ->
    semantic search -> attach live availability to each result -> return
    a ranked shortlist. This is what handles a prompt like "I'm studying
    CS501 and I'm weak in search algorithms, recommend 3 books."
    """
    query = f"{course_code} {weak_topic}" if weak_topic else course_code
    candidates = semantic_search(query, top_k=top_k)

    recommendations = []
    for candidate in candidates:
        availability = get_availability(candidate["book_id"])
        if availability:
            recommendations.append(
                {
                    "book_id": candidate["book_id"],
                    "title": availability["title"],
                    "available_copies": availability["available_copies"],
                    "shelf_location": availability["shelf_location"],
                }
            )

    return {"course_code": course_code, "weak_topic": weak_topic, "recommendations": recommendations}

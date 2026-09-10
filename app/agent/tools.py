"""
agent/tools.py
---------------
Tool schemas (what Claude sees) and the DISPATCH function (what Python
code actually runs) live together deliberately — splitting them tends
to cause them to drift out of sync.

SECURITY NOTE: student_id is intentionally NOT a field in any tool's
input_schema. The LLM never supplies it and can't be prompted into
supplying someone else's — execute_tool() always binds it from the
authenticated JWT (see api/chat.py -> agent/agent.py -> here), the same
trust boundary used in api/circulation.py. Before auth existed, these
tools took student_id as an LLM-provided argument; that would have let
a cleverly-worded chat message act on another student's account.
"""

from app.rag.vector_store import semantic_search
from app.services.book_service import get_availability
from app.services import circulation_service, recommendation_service, student_service

TOOLS = [
    {
        "name": "search_catalog",
        "description": (
            "Semantic search over the library's book catalog. Use for general "
            "'what books exist on X' questions. Does NOT include live availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "description": "default 5"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_availability",
        "description": "Live, real-time copy count and shelf location for a specific book_id.",
        "input_schema": {
            "type": "object",
            "properties": {"book_id": {"type": "string"}},
            "required": ["book_id"],
        },
    },
    {
        "name": "find_best_available_book",
        "description": (
            "For requests like 'give me the best AVAILABLE book on X' or 'I need "
            "something for tomorrow's exam' — chains search + availability + ranking "
            "into a single best recommendation. Prefer this over manually combining "
            "search_catalog and check_availability yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}},
            "required": ["query"],
        },
    },
    {
        "name": "recommend_for_course",
        "description": (
            "For requests like 'I'm studying <course> and weak in <topic>, recommend "
            "some books' — combines course context with topic relevance and returns a "
            "ranked shortlist with availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "course_code": {"type": "string"},
                "weak_topic": {"type": "string", "description": "optional, e.g. 'search algorithms'"},
                "top_k": {"type": "integer"},
            },
            "required": ["course_code"],
        },
    },
    {
        "name": "issue_book",
        "description": "Issue (borrow) the CURRENT student's copy of a book, if one is available. Sets a due date automatically.",
        "input_schema": {
            "type": "object",
            "properties": {"book_id": {"type": "string"}},
            "required": ["book_id"],
        },
    },
    {
        "name": "return_book",
        "description": "Return a book the CURRENT student has issued. Calculates any overdue fine and frees the copy (or notifies the next waitlisted student).",
        "input_schema": {
            "type": "object",
            "properties": {"book_id": {"type": "string"}},
            "required": ["book_id"],
        },
    },
    {
        "name": "renew_book",
        "description": "Renew a book the CURRENT student has issued, if under the max renewal count and nobody else is waiting for it.",
        "input_schema": {
            "type": "object",
            "properties": {"book_id": {"type": "string"}},
            "required": ["book_id"],
        },
    },
    {
        "name": "reserve_book",
        "description": "Join the waitlist, as the CURRENT student, for a book that currently has zero available copies.",
        "input_schema": {
            "type": "object",
            "properties": {"book_id": {"type": "string"}},
            "required": ["book_id"],
        },
    },
    {
        "name": "cancel_reservation",
        "description": "Cancel the CURRENT student's existing waitlist reservation for a book.",
        "input_schema": {
            "type": "object",
            "properties": {"book_id": {"type": "string"}},
            "required": ["book_id"],
        },
    },
    {
        "name": "get_student_dashboard",
        "description": "Get the CURRENT student's full account status: borrowed books, due-soon count, active reservations, outstanding fine.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def execute_tool(name: str, tool_input: dict, student_id: str) -> dict:
    """student_id is always the authenticated caller (see agent.py) — never taken from tool_input."""
    if name == "search_catalog":
        return {"results": semantic_search(tool_input["query"], tool_input.get("top_k", 5))}
    elif name == "check_availability":
        return get_availability(tool_input["book_id"]) or {"error": "book_id not found"}
    elif name == "find_best_available_book":
        return recommendation_service.find_best_available_book(
            tool_input["query"], tool_input.get("top_k", 5)
        )
    elif name == "recommend_for_course":
        return recommendation_service.recommend_for_course(
            tool_input["course_code"], tool_input.get("weak_topic"), tool_input.get("top_k", 3)
        )
    elif name == "issue_book":
        return circulation_service.issue_book(tool_input["book_id"], student_id)
    elif name == "return_book":
        return circulation_service.return_book(tool_input["book_id"], student_id)
    elif name == "renew_book":
        return circulation_service.renew_book(tool_input["book_id"], student_id)
    elif name == "reserve_book":
        return circulation_service.reserve_book(tool_input["book_id"], student_id)
    elif name == "cancel_reservation":
        return circulation_service.cancel_reservation(tool_input["book_id"], student_id)
    elif name == "get_student_dashboard":
        return student_service.get_dashboard(student_id)
    else:
        return {"error": f"Unknown tool: {name}"}

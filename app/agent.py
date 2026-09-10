"""
agent.py
--------
This is the "agentic AI" layer, and it's the part worth explaining
carefully in your Prompt Engineering Journal.

WHAT MAKES THIS "AGENTIC" (vs. plain RAG)?
Plain RAG = retrieve documents -> stuff into a prompt -> generate an answer.
It's a single, fixed pipeline. It can't take ACTIONS or decide dynamically
what to do next.

An agent = the LLM is given a set of TOOLS (Python functions) and, in a
LOOP, decides for itself:
  - "Do I need to search the catalog?" -> calls semantic_search
  - "The user wants to know if it's free?" -> calls check_availability
  - "The user wants to reserve it?" -> calls reserve_book
  - "I now have enough info to answer in plain English" -> stops and replies

This loop (Claude calls a tool -> we run the real Python function -> we
feed the result back to Claude -> repeat) is literally what LangGraph
and other "agent frameworks" do under the hood. We hand-roll it here
directly with the Anthropic API so you (a) fully understand the
mechanism for your journal/viva, and (b) avoid dependency-version
breakage from LangGraph's API changes. Swapping this loop for a
LangGraph `create_react_agent` later is a one-file change if you want
to use it as a "Future Enhancement" bullet.
"""

import json
import anthropic
from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from app.vector_store import semantic_search
from app.database import get_availability, reserve_book, renew_book

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------
# STEP 1: Define the tools. Each tool has a name, a description (Claude
# reads this to decide WHEN to use it — be specific), and a JSON schema
# for its inputs.
# ---------------------------------------------------------------------
TOOLS = [
    {
        "name": "search_catalog",
        "description": (
            "Semantic search over the library's book catalog. Use this whenever "
            "the user is looking for books on a topic, course, or concept — even "
            "if they don't use exact title/author names. Returns candidate books "
            "with a similarity score, NOT live availability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The topic/course/concept to search for."},
                "top_k": {"type": "integer", "description": "How many results to return (default 5)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_availability",
        "description": (
            "Look up LIVE, real-time availability for a specific book_id. Always "
            "call this before telling a user a book is or isn't available — "
            "search_catalog results do NOT include live copy counts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"book_id": {"type": "string"}},
            "required": ["book_id"],
        },
    },
    {
        "name": "reserve_book",
        "description": "Reserve one copy of a book for a student, if a copy is currently available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book_id": {"type": "string"},
                "student_id": {"type": "string", "description": "The student's roll number or ID."},
            },
            "required": ["book_id", "student_id"],
        },
    },
    {
        "name": "renew_book",
        "description": "Renew a book the student currently has issued, extending its due date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "book_id": {"type": "string"},
                "student_id": {"type": "string"},
            },
            "required": ["book_id", "student_id"],
        },
    },
]

# ---------------------------------------------------------------------
# STEP 2: Map tool names -> the real Python functions that execute them.
# This is the "action" half of the agent — Claude only ever DECIDES to
# call a tool; this dictionary is what actually runs it.
# ---------------------------------------------------------------------
def _execute_tool(name: str, tool_input: dict) -> dict:
    if name == "search_catalog":
        results = semantic_search(tool_input["query"], tool_input.get("top_k", 5))
        return {"results": results}
    elif name == "check_availability":
        return get_availability(tool_input["book_id"]) or {"error": "book_id not found"}
    elif name == "reserve_book":
        return reserve_book(tool_input["book_id"], tool_input["student_id"])
    elif name == "renew_book":
        return renew_book(tool_input["book_id"], tool_input["student_id"])
    else:
        return {"error": f"Unknown tool: {name}"}


SYSTEM_PROMPT = """You are the HITK Library Assistant, a helpful AI that helps students
find books, check availability, and manage reservations/renewals.

Rules:
- Always use search_catalog to find books before answering "what books exist on X" questions.
- Always use check_availability before telling a student whether a book is available —
  never guess or rely on search_catalog alone for availability.
- Be concise and specific: mention shelf location when known, and always mention
  live copy counts when discussing availability.
- If a student asks to reserve/renew, confirm the book_id you're acting on before calling
  the tool, unless it's already unambiguous from context.
"""


def run_agent(user_message: str, conversation_history: list[dict] | None = None) -> dict:
    """
    The main agentic loop.

    conversation_history: list of {"role": "user"/"assistant", "content": ...}
    from previous turns, so the agent has memory across a chat session.
    Pass None / [] for a fresh conversation.

    Returns: {"reply": str, "history": updated list, "tool_calls": [debug log]}
    """
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    tool_call_log = []  # purely for your demo/debugging — shows the agent's reasoning trail

    # Loop: keep going until Claude responds WITHOUT requesting a tool call.
    while True:
        response = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Did Claude ask to use a tool, or is it done reasoning?
        if response.stop_reason != "tool_use":
            # Final answer — extract the text block(s) and return.
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            messages.append({"role": "assistant", "content": response.content})
            return {"reply": final_text, "history": messages, "tool_calls": tool_call_log}

        # Claude wants to call one or more tools. Run each, collect results.
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(block.name, block.input)
                tool_call_log.append({"tool": block.name, "input": block.input, "result": result})
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

        # Feed the tool results back to Claude and let the loop continue —
        # it may call another tool, or now have enough info to answer.
        messages.append({"role": "user", "content": tool_results})

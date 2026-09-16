"""
agent.py
--------
This is the "agentic AI" layer, and it's the part worth explaining
carefully in your Prompt Engineering Journal.

WHAT MAKES THIS "AGENTIC" (vs. plain RAG)?
Plain RAG = retrieve documents -> stuff them into a prompt -> generate an answer.
It's a single, fixed pipeline. It can't take ACTIONS or decide dynamically
what to do next.

An agent = the LLM is given a set of TOOLS (Python functions) and, in a
LOOP, decides for itself:
  - "Do I need to search the catalog?" -> calls search_catalog
  - "The user wants to know if it's free?" -> calls check_availability
  - "The user wants to reserve it?" -> calls reserve_book
  - "I now have enough info to answer in plain English" -> stops and replies

This loop (Groq calls a tool -> we run the real Python function -> we
feed the result back to Groq -> repeat) is the agentic mechanism.

We implement the loop directly with the Groq API so the mechanism is
easy to understand for the Prompt Engineering Journal and viva.
"""

import json
from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.vector_store import semantic_search
from app.database import get_availability, reserve_book, renew_book


# ---------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------

_client = Groq(api_key=GROQ_API_KEY)


# ---------------------------------------------------------------------
# STEP 1: Define the tools.
#
# Each tool has:
#   - name
#   - description
#   - JSON schema for its inputs
#
# The LLM reads these descriptions to decide WHEN a tool should be used.
# ---------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": (
                "Semantic search over the library's book catalog. Use this whenever "
                "the user is looking for books on a topic, course, or concept — even "
                "if they don't use exact title or author names. Returns candidate books "
                "with a similarity score, NOT live availability."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic, course, or concept to search for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "How many results to return. Default is 5.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Look up LIVE, real-time availability for a specific book_id. "
                "Always call this before telling a user whether a book is available. "
                "search_catalog results do NOT contain live copy counts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "The unique ID of the book.",
                    }
                },
                "required": ["book_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserve_book",
            "description": (
                "Reserve one copy of a book for a student, if a copy is "
                "currently available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "The unique ID of the book.",
                    },
                    "student_id": {
                        "type": "string",
                        "description": "The student's roll number or ID.",
                    },
                },
                "required": ["book_id", "student_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "renew_book",
            "description": (
                "Renew a book the student currently has issued, extending "
                "its due date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "The unique ID of the book.",
                    },
                    "student_id": {
                        "type": "string",
                        "description": "The student's roll number or ID.",
                    },
                },
                "required": ["book_id", "student_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------
# STEP 2: Map tool names -> the real Python functions that execute them.
#
# The LLM only DECIDES to call a tool.
# This function actually executes the corresponding Python operation.
# ---------------------------------------------------------------------

def _execute_tool(name: str, tool_input: dict) -> dict:

    if name == "search_catalog":
        results = semantic_search(
            tool_input["query"],
            tool_input.get("top_k", 5)
        )
        return {"results": results}

    elif name == "check_availability":
        return (
            get_availability(tool_input["book_id"])
            or {"error": "book_id not found"}
        )

    elif name == "reserve_book":
        return reserve_book(
            tool_input["book_id"],
            tool_input["student_id"]
        )

    elif name == "renew_book":
        return renew_book(
            tool_input["book_id"],
            tool_input["student_id"]
        )

    else:
        return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------

SYSTEM_PROMPT = """You are the HITK Library Assistant, a helpful AI that helps students
find books, check availability, and manage reservations and renewals.

Rules:
- Always use search_catalog to find books before answering "what books exist on X" questions.
- Always use check_availability before telling a student whether a book is available.
- Never guess availability or rely on search_catalog alone for live copy counts.
- Be concise and specific.
- Mention shelf location when known.
- Always mention live copy counts when discussing availability.
- If a student asks to reserve or renew a book, confirm the book_id you are acting on
  before calling the tool, unless it is already unambiguous from the conversation.
"""


# ---------------------------------------------------------------------
# STEP 3: Main agentic loop
# ---------------------------------------------------------------------

def run_agent(
    user_message: str,
    conversation_history: list[dict] | None = None
) -> dict:

    """
    Main agentic loop.

    conversation_history:
        Previous messages from the chat session.

    Returns:
        {
            "reply": str,
            "history": updated conversation history,
            "tool_calls": debug information
        }
    """

    messages = list(conversation_history or [])

    messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    # Used for debugging/demo purposes.
    # This lets us see which tools the agent actually called.
    tool_call_log = []


    # -----------------------------------------------------------------
    # Keep looping until the LLM gives a final answer without
    # requesting another tool.
    # -----------------------------------------------------------------

    while True:

        response = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                *messages
            ],
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1024,
        )


        message = response.choices[0].message


        # -------------------------------------------------------------
        # No tool call -> the agent has enough information and can
        # provide the final answer.
        # -------------------------------------------------------------

        if not message.tool_calls:

            final_text = message.content or ""

            messages.append(
                {
                    "role": "assistant",
                    "content": final_text
                }
            )

            return {
                "reply": final_text,
                "history": messages,
                "tool_calls": tool_call_log
            }


        # -------------------------------------------------------------
        # The LLM requested one or more tools.
        # -------------------------------------------------------------

        assistant_message = {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": []
        }


        for tool_call in message.tool_calls:

            assistant_message["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            )


        messages.append(assistant_message)


        # -------------------------------------------------------------
        # Execute every requested tool.
        # -------------------------------------------------------------

        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name

            try:
                tool_input = json.loads(
                    tool_call.function.arguments
                )
            except json.JSONDecodeError:
                tool_input = {}


            result = _execute_tool(
                tool_name,
                tool_input
            )


            # Save tool call information for debugging/demo purposes.
            tool_call_log.append(
                {
                    "tool": tool_name,
                    "input": tool_input,
                    "result": result,
                }
            )


            # ---------------------------------------------------------
            # Send the real Python tool result back to Groq.
            # Groq can then decide whether another tool is needed or
            # whether it can now answer the student.
            # ---------------------------------------------------------

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )
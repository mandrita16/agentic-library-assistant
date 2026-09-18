"""
app/agent/agent.py
------------------

MindSync LangGraph agent.

Responsibilities:
- Build the LangGraph workflow
- Provide authenticated student context
- Bind library tools to the LLM
- Execute tools when required
- Return the final assistant response
"""

from typing import Annotated, TypedDict

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS


# ============================================================
# AUTHENTICATED CONTEXT
# ============================================================

class AgentContext:
    """
    Runtime context containing the authenticated student.

    Student-specific tools can use this context when needed.
    """

    def __init__(self, student_id: str):
        self.student_id = student_id


# ============================================================
# STATE
# ============================================================

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ============================================================
# LLM
# ============================================================

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0,
)

llm_with_tools = llm.bind_tools(TOOLS)


# ============================================================
# AGENT NODE
# ============================================================

def agent_node(state: AgentState):
    """
    Ask the LLM what to do.

    The model can either:
    - call one or more tools
    - return a normal final response
    """

    messages = [
        SystemMessage(content=SYSTEM_PROMPT)
    ] + state["messages"]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }


# ============================================================
# TOOL NODE
# ============================================================

tool_node = ToolNode(TOOLS)


# ============================================================
# ROUTING
# ============================================================

def should_continue(state: AgentState):
    """
    Route the graph after the agent response.

    AI message with tool calls:
        -> tools

    Normal AI response:
        -> END
    """

    if not state["messages"]:
        return END

    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage):

        if getattr(last_message, "tool_calls", None):
            return "tools"

    return END


# ============================================================
# GRAPH
# ============================================================

workflow = StateGraph(AgentState)

workflow.add_node(
    "agent",
    agent_node,
)

workflow.add_node(
    "tools",
    tool_node,
)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
)

workflow.add_edge(
    "tools",
    "agent",
)

graph = workflow.compile()


# ============================================================
# HISTORY NORMALIZATION
# ============================================================

def normalize_history(
    history: list | None,
) -> list[BaseMessage]:
    """
    Convert API history into LangChain messages.

    Handles malformed history safely.

    Supported formats:

    {
        "role": "user",
        "content": "Hello"
    }

    {
        "role": "assistant",
        "content": "Hi"
    }

    Invalid entries are ignored.
    """

    messages: list[BaseMessage] = []

    if not history:
        return messages

    for item in history:

        # ----------------------------------------------------
        # Protect against:
        # "str object has no attribute get"
        # ----------------------------------------------------

        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content", "")

        # ----------------------------------------------------
        # Content must be a string
        # ----------------------------------------------------

        if not isinstance(content, str):
            continue

        content = content.strip()

        if not content:
            continue

        # ----------------------------------------------------
        # Convert to LangChain messages
        # ----------------------------------------------------

        if role == "user":

            messages.append(
                HumanMessage(
                    content=content
                )
            )

        elif role == "assistant":

            messages.append(
                AIMessage(
                    content=content
                )
            )

    return messages


# ============================================================
# RESPONSE EXTRACTION
# ============================================================

def extract_final_reply(
    messages: list[BaseMessage],
) -> str:
    """
    Extract the final natural-language assistant response.

    Tool-call AI messages are ignored.
    """

    # Search backwards because the final answer
    # should normally be the last AI message.

    for msg in reversed(messages):

        if not isinstance(msg, AIMessage):
            continue

        # Ignore AI messages that only request tools.
        if getattr(msg, "tool_calls", None):
            continue

        content = msg.content

        if isinstance(content, str) and content.strip():
            return content.strip()

        # Some models may return structured content.
        if content:
            return str(content)

    return (
        "I couldn't generate a response. "
        "Please try again."
    )


# ============================================================
# TOOL CALL EXTRACTION
# ============================================================

def extract_tool_calls(
    messages: list[BaseMessage],
) -> list[dict]:
    """
    Extract tool calls for debugging/API visibility.

    Internal reasoning is not exposed.
    """

    tool_calls = []

    for msg in messages:

        if not isinstance(msg, AIMessage):
            continue

        calls = getattr(
            msg,
            "tool_calls",
            [],
        )

        if not calls:
            continue

        for call in calls:

            if not isinstance(call, dict):
                continue

            tool_calls.append(
                {
                    "tool": call.get(
                        "name",
                        "unknown",
                    ),
                    "input": call.get(
                        "args",
                        {},
                    ),
                }
            )

    return tool_calls


# ============================================================
# CLEAN HISTORY
# ============================================================

def build_clean_history(
    messages: list[BaseMessage],
) -> list[dict]:
    """
    Build frontend-friendly conversation history.

    Tool messages and tool-call internals are excluded.
    """

    history = []

    for msg in messages:

        # ----------------------------------------------------
        # USER
        # ----------------------------------------------------

        if isinstance(msg, HumanMessage):

            content = msg.content

            if isinstance(content, str) and content.strip():

                history.append(
                    {
                        "role": "user",
                        "content": content,
                    }
                )

        # ----------------------------------------------------
        # ASSISTANT
        # ----------------------------------------------------

        elif isinstance(msg, AIMessage):

            # Do not expose tool-call messages.

            if getattr(
                msg,
                "tool_calls",
                None,
            ):
                continue

            content = msg.content

            if isinstance(
                content,
                str,
            ) and content.strip():

                history.append(
                    {
                        "role": "assistant",
                        "content": content,
                    }
                )

    return history


# ============================================================
# PUBLIC API
# ============================================================

def run_agent(
    message: str,
    student_id: str,
    history: list | None = None,
):
    """
    Run MindSync for an authenticated student.

    Args:
        message:
            Current user message.

        student_id:
            Authenticated student ID.

        history:
            Previous conversation history.

    Returns:
        Dictionary containing:
        - reply
        - history
        - tool_calls
        - message_count
        - message_types
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    if not isinstance(message, str):
        message = str(message)

    message = message.strip()

    if not message:

        return {
            "reply": "Please enter a message.",
            "history": [],
            "tool_calls": [],
            "message_count": 0,
            "message_types": [],
        }

    # ========================================================
    # BUILD MESSAGES
    # ========================================================

    messages = normalize_history(history)

    # Add current user message.

    messages.append(
        HumanMessage(
            content=message
        )
    )

    # ========================================================
    # AUTHENTICATED CONTEXT
    # ========================================================

    context = AgentContext(
        student_id=student_id
    )

    # ========================================================
    # RUN LANGGRAPH
    # ========================================================

    result = graph.invoke(
        {
            "messages": messages,
        },
        context=context,
        config={
            # Enough for:
            # agent -> tool -> agent
            # without allowing an endless loop.
            "recursion_limit": 12,
        },
    )

    result_messages = result.get(
        "messages",
        [],
    )

    # ========================================================
    # FINAL REPLY
    # ========================================================

    reply = extract_final_reply(
        result_messages
    )

    # ========================================================
    # TOOL CALLS
    # ========================================================

    tool_calls = extract_tool_calls(
        result_messages
    )

    # ========================================================
    # CLEAN HISTORY
    # ========================================================

    output_history = build_clean_history(
        result_messages
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "reply": reply,
        "history": output_history,
        "tool_calls": tool_calls,
        "message_count": len(
            result_messages
        ),
        "message_types": [
            type(msg).__name__
            for msg in result_messages
        ],
    }
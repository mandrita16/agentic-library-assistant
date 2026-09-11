"""
agent/agent.py
--------------

LangGraph-based agent for MindSync.

Workflow:
1. Receive the student's message.
2. Send the message to Claude through LangChain.
3. Claude decides whether a tool is required.
4. LangGraph executes the selected tool.
5. Tool results are returned to Claude.
6. Claude can call additional tools when necessary.
7. When no more tools are required, Claude produces the final answer.
"""

from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS


# ===================================================================
# MODEL
# ===================================================================

llm = ChatAnthropic(
    model=CLAUDE_MODEL,
    anthropic_api_key=ANTHROPIC_API_KEY,
    max_tokens=2048,
)

# Give Claude access to the MindSync tools.
llm_with_tools = llm.bind_tools(TOOLS)


# ===================================================================
# GRAPH STATE
# ===================================================================

class AgentState(TypedDict):
    """
    State maintained by LangGraph during a conversation.
    """

    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]


# ===================================================================
# AGENT NODE
# ===================================================================

def agent_node(state: AgentState):
    """
    Ask Claude what should happen next.

    Claude may either:
    - produce a normal response, or
    - request one or more tools.
    """

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT
        )
    ] + state["messages"]

    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response]
    }


# ===================================================================
# ROUTING
# ===================================================================

def should_continue(state: AgentState):
    """
    Decide whether LangGraph should execute tools or finish.

    If Claude requested a tool:
        route to ToolNode.

    Otherwise:
        finish the graph.
    """

    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage):
        if last_message.tool_calls:
            return "tools"

    return END


# ===================================================================
# TOOL NODE
# ===================================================================

tool_node = ToolNode(TOOLS)


# ===================================================================
# BUILD LANGGRAPH
# ===================================================================

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
    {
        "tools": "tools",
        END: END,
    },
)

workflow.add_edge(
    "tools",
    "agent",
)


# Compile the graph.
graph = workflow.compile()


# ===================================================================
# PUBLIC AGENT FUNCTION
# ===================================================================

def run_agent(
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Run the MindSync LangGraph agent.

    Parameters
    ----------
    user_message:
        Current message from the student.

    conversation_history:
        Previous conversation messages.

    Returns
    -------
    dict
        {
            "reply": str,
            "history": list,
            "tool_calls": list
        }
    """

    messages: list[BaseMessage] = []

    # ---------------------------------------------------------------
    # Convert existing history into LangChain messages
    # ---------------------------------------------------------------

    for message in conversation_history or []:

        role = message.get("role")
        content = message.get("content", "")

        if not isinstance(content, str):
            continue

        if role == "user":

            messages.append(
                HumanMessage(
                    content=content,
                )
            )

        elif role == "assistant":

            messages.append(
                AIMessage(
                    content=content,
                )
            )

    # ---------------------------------------------------------------
    # Add current user message
    # ---------------------------------------------------------------

    messages.append(
        HumanMessage(
            content=user_message,
        )
    )

    # ---------------------------------------------------------------
    # Run LangGraph
    # ---------------------------------------------------------------

    result = graph.invoke(
        {
            "messages": messages,
        },
        config={
            # Prevent an uncontrolled agent/tool loop.
            "recursion_limit": 20,
        },
    )

    final_messages = result["messages"]

    # ---------------------------------------------------------------
    # Extract final AI response
    # ---------------------------------------------------------------

    reply = ""

    for message in reversed(final_messages):

        if not isinstance(message, AIMessage):
            continue

        # Ignore AI messages that are requesting tools.
        if message.tool_calls:
            continue

        if isinstance(message.content, str):

            reply = message.content

        elif isinstance(message.content, list):

            text_parts = []

            for block in message.content:

                if (
                    isinstance(block, dict)
                    and block.get("type") == "text"
                ):
                    text_parts.append(
                        block.get("text", "")
                    )

            reply = "".join(text_parts)

        break

    # ---------------------------------------------------------------
    # Collect tool calls
    # ---------------------------------------------------------------

    tool_calls = []

    for message in final_messages:

        if not isinstance(message, AIMessage):
            continue

        for call in message.tool_calls:

            tool_calls.append(
                {
                    "tool": call.get("name"),
                    "input": call.get("args", {}),
                }
            )

    # ---------------------------------------------------------------
    # Build simple conversation history
    # ---------------------------------------------------------------

    history = []

    for message in final_messages:

        if isinstance(message, HumanMessage):

            history.append(
                {
                    "role": "user",
                    "content": message.content,
                }
            )

        elif isinstance(message, AIMessage):

            # Do not expose intermediate tool-call messages
            # as normal assistant responses.
            if message.tool_calls:
                continue

            if isinstance(message.content, str):

                history.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                    }
                )

            elif isinstance(message.content, list):

                text_parts = []

                for block in message.content:

                    if (
                        isinstance(block, dict)
                        and block.get("type") == "text"
                    ):
                        text_parts.append(
                            block.get("text", "")
                        )

                content = "".join(text_parts)

                if content:
                    history.append(
                        {
                            "role": "assistant",
                            "content": content,
                        }
                    )

    return {
        "reply": reply.strip(),
        "history": history,
        "tool_calls": tool_calls,
    }
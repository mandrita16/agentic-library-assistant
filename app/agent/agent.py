"""
agent/agent.py
--------------
Groq-based agent for MindSync.

Workflow:
1. Receive the student's message.
2. Send the message to Groq.
3. Groq decides whether a tool is required.
4. Execute the selected MindSync tool.
5. Send the tool result back to Groq.
6. Groq can call additional tools when necessary.
7. When no more tools are required, Groq produces the final answer.

The existing tools in app.agent.tools are reused.
"""

import json

from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS


# ===================================================================
# GROQ CLIENT
# ===================================================================

client = Groq(
    api_key=GROQ_API_KEY
)


# ===================================================================
# TOOL REGISTRY
# ===================================================================

# Keep the existing LangChain tools and make them easy to execute
# by name when Groq requests a function call.

TOOL_REGISTRY = {
    tool.name: tool
    for tool in TOOLS
}


# ===================================================================
# CONVERT LANGCHAIN TOOLS TO GROQ TOOL SCHEMAS
# ===================================================================

def _build_tool_schemas():
    """
    Convert the existing LangChain @tool functions into the
    OpenAI-compatible function schema expected by Groq.
    """

    schemas = []

    for tool in TOOLS:

        # LangChain tools created with @tool expose their
        # argument schema through args_schema.
        parameters = tool.args_schema.model_json_schema()

        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": parameters,
                },
            }
        )

    return schemas


GROQ_TOOLS = _build_tool_schemas()


# ===================================================================
# TOOL EXECUTION
# ===================================================================

def _execute_tool(
    name: str,
    arguments: dict,
) -> dict:
    """
    Execute one of the existing MindSync LangChain tools.
    """

    tool = TOOL_REGISTRY.get(name)

    if tool is None:
        return {
            "success": False,
            "error": f"Unknown tool: {name}",
        }

    try:

        result = tool.invoke(arguments)

        # Most MindSync tools already return dictionaries.
        if isinstance(result, dict):
            return result

        return {
            "result": result
        }

    except Exception as exc:

        return {
            "success": False,
            "error": str(exc),
        }


# ===================================================================
# PUBLIC AGENT FUNCTION
# ===================================================================

def run_agent(
    user_message: str,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Run the MindSync Groq agent.

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

    # ---------------------------------------------------------------
    # BUILD MESSAGE HISTORY
    # ---------------------------------------------------------------

    messages = []

    for message in conversation_history or []:

        role = message.get("role")
        content = message.get("content", "")

        if role not in {"user", "assistant"}:
            continue

        if not isinstance(content, str):
            continue

        messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    # ---------------------------------------------------------------
    # CURRENT USER MESSAGE
    # ---------------------------------------------------------------

    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    # ---------------------------------------------------------------
    # TOOL CALL LOG
    # ---------------------------------------------------------------

    tool_call_log = []

    # ---------------------------------------------------------------
    # AGENT LOOP
    # ---------------------------------------------------------------

    for _ in range(10):

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                *messages,
            ],
            tools=GROQ_TOOLS,
            tool_choice="auto",
            max_tokens=2048,
        )

        message = response.choices[0].message

        # -----------------------------------------------------------
        # NO TOOL CALL
        # -----------------------------------------------------------

        if not message.tool_calls:

            reply = message.content or ""

            final_history = list(messages)

            final_history.append(
                {
                    "role": "assistant",
                    "content": reply,
                }
            )

            return {
                "reply": reply.strip(),
                "history": final_history,
                "tool_calls": tool_call_log,
            }

        # -----------------------------------------------------------
        # ASSISTANT TOOL-CALL MESSAGE
        # -----------------------------------------------------------

        assistant_tool_calls = []

        for tool_call in message.tool_calls:

            assistant_tool_calls.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            )

        messages.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": assistant_tool_calls,
            }
        )

        # -----------------------------------------------------------
        # EXECUTE TOOLS
        # -----------------------------------------------------------

        for tool_call in message.tool_calls:

            tool_name = tool_call.function.name
            raw_arguments = tool_call.function.arguments

            try:

                arguments = json.loads(
                    raw_arguments
                )

            except json.JSONDecodeError:

                arguments = {}

            result = _execute_tool(
                tool_name,
                arguments,
            )

            # Save tool execution for API/frontend/debugging.
            tool_call_log.append(
                {
                    "tool": tool_name,
                    "input": arguments,
                    "result": result,
                }
            )

            # -------------------------------------------------------
            # SEND TOOL RESULT BACK TO GROQ
            # -------------------------------------------------------

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        result,
                        default=str,
                    ),
                }
            )

    # =================================================================
    # SAFETY FALLBACK
    # =================================================================

    return {
        "reply": (
            "I couldn't complete that request within the allowed "
            "number of reasoning steps."
        ),
        "history": messages,
        "tool_calls": tool_call_log,
    }
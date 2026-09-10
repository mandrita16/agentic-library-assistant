"""
agent/agent.py
---------------
The agentic loop: Claude decides which tool(s) to call, we run the real
Python function, feed the result back, repeat until Claude has enough
information to answer in plain English.

student_id flows in from api/chat.py (which got it from the JWT, not
from the request body) and is passed to every execute_tool() call —
the model never sees or controls this value.
"""

import json
import anthropic
from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from app.agent.prompts import build_system_prompt
from app.agent.tools import TOOLS, execute_tool

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def run_agent(user_message: str, student_id: str, conversation_history: list[dict] | None = None) -> dict:
    """
    student_id: the authenticated student this conversation belongs to
    (see api/chat.py) — bound into every tool call and into the system prompt.

    conversation_history: list of {"role": ..., "content": ...} from
    previous turns — pass back what this function returned last time as
    `history` to keep a multi-turn conversation. Pass None/[] to start fresh.

    Returns: {"reply": str, "history": updated list, "tool_calls": [debug log]}
    """
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    tool_call_log = []  # for your demo — shows the agent's reasoning/action trail
    system_prompt = build_system_prompt(student_id)

    while True:
        response = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final_text = "".join(block.text for block in response.content if block.type == "text")
            messages.append({"role": "assistant", "content": response.content})
            return {"reply": final_text, "history": messages, "tool_calls": tool_call_log}

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input, student_id)
                tool_call_log.append({"tool": block.name, "input": block.input, "result": result})
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)}
                )

        messages.append({"role": "user", "content": tool_results})

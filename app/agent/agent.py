"""
agent/agent.py
---------------
The agentic loop itself: Claude decides which tool(s) to call, we run
the real Python function, feed the result back, and repeat until Claude
has enough information to answer in plain English. This loop is the
same mechanism LangGraph's `create_react_agent` implements internally —
hand-rolled here so it's fully transparent for your journal/viva and has
no dependency-version fragility.
"""

import json
import anthropic
from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS, execute_tool

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def run_agent(user_message: str, conversation_history: list[dict] | None = None) -> dict:
    """
    conversation_history: list of {"role": ..., "content": ...} from
    previous turns — pass back what this function returned last time as
    `history` to keep a multi-turn conversation. Pass None/[] to start fresh.

    Returns: {"reply": str, "history": updated list, "tool_calls": [debug log]}
    """
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    tool_call_log = []  # for your demo — shows the agent's reasoning/action trail

    while True:
        response = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
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
                result = execute_tool(block.name, block.input)
                tool_call_log.append({"tool": block.name, "input": block.input, "result": result})
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)}
                )

        messages.append({"role": "user", "content": tool_results})

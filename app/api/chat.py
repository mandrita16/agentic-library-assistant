"""
app/api/chat.py
---------------

Chat API endpoint for MindSync.

Handles:
- authenticated student context
- conversation history
- forwarding requests to the LangGraph agent
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.agent.agent import run_agent
from app.auth.dependencies import get_current_student


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Student's message",
    )

    history: list[dict] = Field(
        default_factory=list,
        description="Previous conversation messages",
    )


# ============================================================
# CHAT ENDPOINT
# ============================================================

@router.post("")
def chat_with_mindsync(
    req: ChatRequest,
    current_student_id: str = Depends(
        get_current_student
    ),
):

    try:

        result = run_agent(
            message=req.message,
            student_id=current_student_id,
            history=req.history,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
          detail=f"MindSync agent error: {str(exc)}",
        )
"""
api/chat.py
-----------
Main conversational endpoint for MindSync.

The endpoint receives a student message and optional
conversation history and sends them to the MindSync agent.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.agent import run_agent


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Student's message"
    )

    history: list[dict] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )


@router.post("")
def chat_with_mindsync(req: ChatRequest):
    """
    Send a message to MindSync.

    Example request:

    {
        "message": "Find me books on machine learning",
        "history": []
    }
    """

    try:
        result = run_agent(
            req.message,
            req.history
        )

        return result

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MindSync agent error: {str(exc)}"
        )
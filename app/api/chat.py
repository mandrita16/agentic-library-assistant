"""
api/chat.py
-----------
The single conversational entry point — now behind auth. student_id
never appears in the request body; it comes from the JWT and is bound
into every tool call the agent makes for this conversation.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.agent.agent import run_agent
from app.auth.dependencies import get_current_student

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("")
def chat(req: ChatRequest, student_id: str = Depends(get_current_student)):
    """Example body: {"message": "find me books on NLP for CS603", "history": []}. Requires Authorization: Bearer <token>."""
    return run_agent(req.message, student_id, req.history)

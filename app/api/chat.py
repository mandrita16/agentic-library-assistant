"""
api/chat.py
-----------
The single conversational entry point — everything else in api/ is a
direct, non-agentic shortcut for a plain UI that doesn't need chat.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.agent.agent import run_agent

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("")
def chat(req: ChatRequest):
    """Example body: {"message": "find me books on NLP for CS603", "history": []}"""
    return run_agent(req.message, req.history)

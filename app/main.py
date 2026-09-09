"""
main.py
-------
The API layer. This is the ONLY file a frontend (React, or even a plain
HTML page) would talk to — it hides all the RAG/agent/DB complexity
behind three simple endpoints.

Run with (from project root, venv active):
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for an interactive Swagger UI —
this alone is a great live demo for your ideathon presentation, no
frontend needed.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import run_agent
from app.vector_store import semantic_search
from app.database import get_availability, reserve_book

app = FastAPI(title="HITK Library AI Assistant")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []  # pass back what /chat returned last time, for memory


class ReserveRequest(BaseModel):
    book_id: str
    student_id: str


@app.get("/")
def root():
    return {"status": "ok", "service": "HITK Library AI Assistant"}


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Main entry point — natural-language conversation with the agent.
    Example body: {"message": "find me books on NLP for CS603", "history": []}
    """
    result = run_agent(req.message, req.history)
    return result


@app.get("/search")
def search(q: str, top_k: int = 5):
    """
    Direct semantic search endpoint, bypassing the agent — useful for a
    simple search-bar UI that doesn't need conversational back-and-forth.
    """
    return {"results": semantic_search(q, top_k)}


@app.get("/availability/{book_id}")
def availability(book_id: str):
    result = get_availability(book_id)
    if result is None:
        return {"error": "Book not found"}
    return result


@app.post("/reserve")
def reserve(req: ReserveRequest):
    return reserve_book(req.book_id, req.student_id)

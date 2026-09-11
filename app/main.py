"""
main.py
-------
Application entry point for MindSync.

This file only creates the FastAPI application and
registers the routers from app/api/.

Business logic is handled by:
    api/ → services/ → database / RAG

Run from the project root with the virtual environment active:

    uvicorn app.main:app --reload

Swagger UI:
    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from app.api import chat, books, students, circulation, admin


app = FastAPI(
    title="MindSync — Smart Library & Academic Assistant",
    description="AI-powered library and academic assistant for students.",
    version="1.0.0"
)


# Register API routers
app.include_router(chat.router)
app.include_router(books.router)
app.include_router(students.router)
app.include_router(circulation.router)
app.include_router(admin.router)


@app.get("/", tags=["system"])
def root():
    """
    Basic health check for the application.
    """

    return {
        "status": "ok",
        "service": "MindSync",
        "version": "1.0.0"
    }
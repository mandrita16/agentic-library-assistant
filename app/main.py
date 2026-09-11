"""
main.py
-------
Application entry point for MindSync.

This file creates the FastAPI application, registers the API routers,
and serves the static frontend.

Architecture:

    API → Services → Database / RAG

Run from the project root with the virtual environment active:

    python -m uvicorn app.main:app --reload

Swagger UI:

    http://127.0.0.1:8000/docs

Frontend:

    http://127.0.0.1:8000/
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    auth,
    chat,
    books,
    students,
    circulation,
    admin,
)


# ===================================================================
# FASTAPI APPLICATION
# ===================================================================

app = FastAPI(
    title="MindSync — Smart Library & Academic Assistant",
    description="AI-powered library and academic assistant for students.",
    version="1.0.0",
)


# ===================================================================
# CORS
# ===================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================================================================
# API ROUTERS
# ===================================================================

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(books.router)
app.include_router(students.router)
app.include_router(circulation.router)
app.include_router(admin.router)


# ===================================================================
# HEALTH CHECK
# ===================================================================

@app.get("/", tags=["system"])
def root():
    """
    Basic health check for the application.
    """

    return {
        "status": "ok",
        "service": "MindSync",
        "version": "1.0.0",
    }


# ===================================================================
# STATIC FRONTEND
# ===================================================================

# The static frontend is served from the /static directory.
#
# NOTE:
# This mount is intentionally placed AFTER the API routes so that
# the API endpoints remain available.

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)

app.mount(
    "/",
    StaticFiles(
        directory="static",
        html=True,
    ),
    name="frontend",
)
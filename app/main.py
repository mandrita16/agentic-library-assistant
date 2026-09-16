"""
app/main.py
-----------
Application entry point for MindSync.

MindSync is an AI-powered Smart Library & Academic Assistant
built with FastAPI, LangGraph, LangChain, Groq, MongoDB, and ChromaDB.

Architecture:

    Frontend
        ↓
    FastAPI API Layer
        ↓
    Authentication / LangGraph Agent
        ↓
    Tools
        ↓
    Services
        ↓
    MongoDB / ChromaDB

Run from the project root:

    python -m uvicorn app.main:app --reload

Swagger UI:

    http://127.0.0.1:8000/docs

Frontend:

    http://127.0.0.1:8000/
"""

from pathlib import Path

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


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_DIR = BASE_DIR / "static"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="MindSync — Smart Library & Academic Assistant",
    description=(
        "AI-powered library and academic assistant for students. "
        "MindSync combines semantic book search, live library data, "
        "personalized recommendations, and library circulation services."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API ROUTERS
# ============================================================

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(books.router)
app.include_router(students.router)
app.include_router(circulation.router)
app.include_router(admin.router)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health", tags=["system"])
def health_check():
    """
    Health check endpoint.
    """

    return {
        "status": "healthy",
        "service": "MindSync",
        "version": "1.0.0",
    }


# ============================================================
# STATIC FRONTEND
# ============================================================

if not STATIC_DIR.exists():
    raise RuntimeError(
        f"Static frontend directory not found: {STATIC_DIR}"
    )


# Serve JavaScript, CSS, images, etc.
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


# Serve index.html at /
#
# IMPORTANT:
# This must be registered without another @app.get("/")
# endpoint above it. Otherwise FastAPI would return JSON
# instead of serving the MindSync frontend.
app.mount(
    "/",
    StaticFiles(
        directory=STATIC_DIR,
        html=True,
    ),
    name="frontend",
)
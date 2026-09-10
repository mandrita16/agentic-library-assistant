"""
main.py
-------
Wiring: creates the FastAPI app, mounts each router from app/api/, and
serves the static frontend (static/index.html) at "/". CORS is enabled
so the same page could also be opened as a plain file:// during
development without requests being blocked — with everything served
from this one app in production/demo use, CORS isn't strictly required,
but it costs nothing to leave on for a hackathon-scale project.

Run with (from project root, venv active):
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/  for the chat UI
        http://127.0.0.1:8000/docs for the Swagger API explorer
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, chat, books, students, circulation, admin

app = FastAPI(title="HITK AI Library Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(books.router)
app.include_router(students.router)
app.include_router(circulation.router)
app.include_router(admin.router)

# Serves static/index.html at "/" and static/* at "/static/*".
# html=True makes StaticFiles fall back to index.html for the root path.
app.mount("/", StaticFiles(directory="static", html=True), name="static")

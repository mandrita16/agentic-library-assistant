"""
main.py
-------
Just wiring: creates the FastAPI app and mounts each router from app/api/.
All actual logic lives in api/*.py -> services/*.py -> database or rag.

Run with (from project root, venv active):
    uvicorn app.main:app --reload
Then open http://127.0.0.1:8000/docs for the interactive Swagger UI.
"""

from fastapi import FastAPI
from app.api import chat, books, students, circulation, admin

app = FastAPI(title="HITK AI Library Management System")

app.include_router(chat.router)
app.include_router(books.router)
app.include_router(students.router)
app.include_router(circulation.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "HITK AI Library Management System"}

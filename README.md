# HITK Library AI Assistant — Setup Guide (Windows / VS Code / PowerShell)

## What you're building
A RAG + agentic AI assistant for the college library:
- **RAG**: local embeddings (sentence-transformers) + ChromaDB vector search over your book catalog
- **Agentic**: Claude decides which tool to call — search, check availability, reserve, renew — in a loop, instead of a single fixed pipeline
- **Structured data**: MongoDB holds live availability/circulation state (this is the part vector search can't do reliably)

This two-store design (vectors for *meaning*, MongoDB for *live facts*) is the core architecture decision — explain it explicitly in your Solution Blueprint doc, it's a strong "originality" point.

---

## Prerequisites

1. **Python 3.11+** — check with:
   ```powershell
   python --version
   ```
   If missing, install from python.org and make sure "Add to PATH" is checked during install.

2. **MongoDB Community Server** — download from mongodb.com/try/download/community, install with default options. After install, MongoDB runs automatically as a Windows service on `localhost:27017` — you don't need to start anything manually.

3. **An Anthropic API key** — sign up at console.anthropic.com, create a key. You'll paste it into `.env` in Step 4 below.

---

## Step 1 — Open the project in VS Code

```powershell
cd path\to\library_ai_assistant
code .
```

Open a terminal inside VS Code: **Terminal → New Terminal** (it defaults to PowerShell on Windows).

---

## Step 2 — Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**If you get an error about "running scripts is disabled on this system":**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then re-run the activate command. You'll know it worked when your terminal prompt shows `(venv)` at the start.

---

## Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

This will take a few minutes the first time — `sentence-transformers` and `chromadb` pull in PyTorch, which is a large download. Grab a chai while it installs.

---

## Step 4 — Configure environment variables

```powershell
copy .env.example .env
```

Open the new `.env` file in VS Code and paste in your real Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```
Leave `MONGO_URI` as-is if you installed MongoDB with default settings.

---

## Step 5 — Seed the database and build the vector index

This is a **one-time step** (run it again only if you edit `data/sample_books.json`):

```powershell
python -m app.ingest
```

Expected output:
```
[ingest] Loaded 8 books from data/sample_books.json
[ingest] MongoDB seeded.
[vector_store] Indexed 8 books into ChromaDB.
[ingest] ChromaDB vector index built. Ingestion complete.
```

The first run will also download the embedding model (~80MB) — this only happens once, it's cached afterward.

---

## Step 6 — Run the API server

```powershell
uvicorn app.main:app --reload
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
```

---

## Step 7 — Try it out

Open **http://127.0.0.1:8000/docs** in your browser — this is FastAPI's auto-generated Swagger UI. Use it to test without writing any frontend code:

- **POST /chat** — try `{"message": "I need books on NLP for CS603", "history": []}`
  Watch it call `search_catalog`, then `check_availability`, then answer in plain English.
- **GET /search?q=machine learning** — raw semantic search, no agent reasoning
- **POST /reserve** — try `{"book_id": "B001", "student_id": "S12345"}`

For a multi-turn conversation, take the `"history"` field FROM the response of one `/chat` call and pass it back INTO the next call's request body — that's how the agent remembers earlier turns.

---

## Project structure
```
library_ai_assistant/
├── app/
│   ├── config.py       # all settings, loaded from .env
│   ├── database.py     # MongoDB: live availability, reservations
│   ├── vector_store.py # ChromaDB: semantic search over catalog
│   ├── agent.py         # the agentic loop (Claude + tools)
│   ├── ingest.py        # one-time seed script
│   └── main.py           # FastAPI endpoints
├── data/
│   └── sample_books.json
├── requirements.txt
├── .env.example
└── README.md
```

## For your Prompt Engineering Journal / Blueprint doc
Good things to screenshot/document from this build:
1. The `/docs` Swagger UI in action — proof of a working API
2. A `/chat` request/response pair showing the tool-call trail (`tool_calls` field in the response) — this IS your "agentic AI" evidence
3. The two-store architecture diagram (ask me to generate this next if you'd like a visual)

## Extending this later (good "Future Enhancements" bullets)
- Swap the hand-rolled agent loop in `agent.py` for LangGraph's `create_react_agent` (same pattern you used in SentinelOps)
- Add a `/recommend` endpoint that chains: student's course list → search_catalog per course → dedupe/rank
- Voice input via a speech-to-text layer in front of `/chat`
- Multi-language (Bengali/English) support in the system prompt
=======


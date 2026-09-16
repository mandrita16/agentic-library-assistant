<div align="center">

<img src="https://media2.giphy.com/media/dUsblht9Hs4abHk8aG/giphy.gif" width="500"/>

# 📚 HITK Library AI Assistant

###  Agentic RAG-powered AI Assistant for Intelligent Library Management
**FastAPI · Groq · ChromaDB · MongoDB Atlas · RAG · Agentic Tool Calling**

</div>

## What we are building
A RAG + agentic AI assistant for the college library:
- **RAG**: local embeddings (sentence-transformers) + ChromaDB vector search over your book catalog
- **Agentic**: Claude decides which tool to call — search, check availability, reserve, renew — in a loop, instead of a single fixed pipeline
- **Structured data**: MongoDB holds live availability/circulation state (this is the part vector search can't do reliably)

This two-store design (vectors for *meaning*, MongoDB for *live facts*) is the core architecture decision — explain it explicitly in your Solution Blueprint doc, it's a strong "originality" point.

---
## 🚀 Overview

**MindSync** is an AI-powered library assistant designed to make college library management more intelligent, interactive, and personalized.

Instead of functioning as a simple chatbot, MindSync uses an **agentic AI architecture** where the AI dynamically decides which tools it needs to answer a user's request.

MindSync can:

- 🔎 Search the library catalog using semantic search
- 📚 Check real-time book availability
- 📌 Reserve books
- 🔄 Renew books
- 📖 Issue and return books
- 🎯 Recommend books based on courses, goals, skills, or mood
- 👤 Provide personalized student information
- 📊 Support library management and analytics
- 💬 Maintain conversational context

The system combines **Retrieval-Augmented Generation (RAG)**, **LLM reasoning**, and **structured database operations** into a single intelligent library assistant.

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

## Step 1 — Clone the repository

```powershell
git clone https://github.com/mandrita16/agentic-library-assistant.git
cd agentic-library-assistant
```

---

## Step 2 — Create and activate a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

---

## Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

---

## Step 4 — Configure environment variables

```powershell
copy .env.example .env
```

Open the new `.env` file in VS Code and paste in your real Anthropic API key:
```
GROQ_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
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
## Architecture
```mermaid
flowchart TD
  U[👤 Student] --> API[⚡ FastAPI Backend]
  API --> AGENT[🤖 Groq Agent]
  AGENT --> DECIDE{Tool Selection}
  DECIDE --> SEARCH[🔎 search_catalog]
  DECIDE --> AVAIL[📚 check_availability]
  DECIDE --> RESERVE[📌 reserve_book]
  DECIDE --> RENEW[🔄 renew_book]
  SEARCH --> EMBED[🧠 Sentence-Transformers]
  EMBED --> CHROMA[(🟠 ChromaDB)]
  AVAIL --> MONGO[(🍃 MongoDB)]
  RESERVE --> MONGO
  RENEW --> MONGO
  CHROMA --> AGENT
  MONGO --> AGENT
  AGENT --> RESPONSE[💬 Natural Language Response]
  RESPONSE --> U
```

  ---

**Agentic Request Flow**

```mermaid
flowchart LR
  UQ([User Query]) --> API[FastAPI]
  API --> GROQ[Groq Agent]
  GROQ -->|Search Catalog| CHROMA[ChromaDB]
  GROQ -->|Check Availability| MONGO[MongoDB]
  GROQ -->|Reserve Book| MONGO
  GROQ -->|Renew Loan| MONGO
  CHROMA --> CLAUDE
  MONGO --> CLAUDE
  GROQ --> RESP[Final Natural-language Response]
```

Unlike a traditional RAG pipeline:
```
Query → Retrieve → Generate
```

This project follows:

```
User Query
    ↓
Groq LLM
    ↓
Choose Tool
    ↓
Execute Tool
    ↓
Observe Result
    ↓
Choose Another Tool if Required
    ↓
Final Response
```

##  Example

User Request

I need books on NLP for CS603.

Which ones are available?

### Agent Execution
```
1. User sends request
          ↓
2. FastAPI receives request
          ↓
3. Groq agent analyzes the request
          ↓
4. Agent calls search_catalog
          ↓
5. ChromaDB retrieves relevant books
          ↓
6. Agent identifies relevant results
          ↓
7. Agent calls check_availability
          ↓
8. MongoDB Atlas provides live availability
          ↓
9. Agent generates final response
          ↓
10. User receives the answer
```
   ```
              MindSync
                    │
          ┌─────────┴─────────┐
          │                   │
      ChromaDB          MongoDB Atlas
          │                   │
  Semantic Search       Live Library State
          │                   │
          └─────────┬─────────┘
                    │
                AI Agent
                    │
              Final Answer
   ```
           
### Example Response

I found 3 books relevant to NLP and CS603.

1. Natural Language Processing with Python
   Available: Yes

2. Speech and Language Processing
   Available: No

3. Foundations of Statistical Natural Language Processing
   Available: Yes
   
---

## Project structure
```
library_ai_assistant/
│
├── requirements.txt
├── .env
├── README.md
│
├── data/
│   └── sample_books.json
│
└── app/
    ├── __init__.py
    ├── config.py
    ├── ingest.py
    ├── main.py
    │
    ├── database/
    │   ├── __init__.py
    │   ├── mongo.py
    │   └── models.py
    │
    ├── rag/
    │   ├── __init__.py
    │   ├── embeddings.py
    │   └── vector_store.py
    │
    ├── services/
    │   ├── __init__.py
    │   ├── book_service.py
    │   ├── circulation_service.py
    │   ├── fine_service.py
    │   ├── recommendation_service.py
    │   ├── student_service.py
    │   └── analytics_service.py
    │
    ├── agent/
    │   ├── __init__.py
    │   ├── prompts.py
    │   ├── tools.py
    │   └── agent.py
    │
    └── api/
        ├── __init__.py
        ├── chat.py
        ├── books.py
        ├── students.py
        ├── circulation.py
        └── admin.py

```
---
## 🚀 Live Demo

MindSync:
```
https://agentic-library-assistant-production.up.railway.app/
```
---
## For your Prompt Engineering Journal / Blueprint doc
Good things to screenshot/document from this build:
1. The `/docs` Swagger UI in action — proof of a working API
2. A `/chat` request/response pair showing the tool-call trail (`tool_calls` field in the response) — this IS your "agentic AI" evidence
3. The two-store architecture diagram (ask me to generate this next if you'd like a visual)

## Extending this later 
- Swap the hand-rolled agent loop in `agent.py` for LangGraph's `create_react_agent` (same pattern you used in SentinelOps)
- Add a `/recommend` endpoint that chains: student's course list → search_catalog per course → dedupe/rank
- Voice input via a speech-to-text layer in front of `/chat`
- Multi-language (Bengali/English) support in the system prompt



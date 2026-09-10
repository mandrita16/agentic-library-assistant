# HITK AI Library Management System — Setup Guide (Windows / VS Code / PowerShell)

## What you're building
A full RAG + agentic AI library management system with a real login-gated frontend:
- **RAG**: local embeddings (sentence-transformers) + ChromaDB over the book catalog
- **Agentic**: Claude chooses from 10 tools — search, availability, recommend-for-course,
  find-best-available-book, issue, return, renew, reserve, cancel-reservation, dashboard —
  deciding for itself which to call, in a loop
- **Circulation**: real issue/return/renew with due dates, a reservation waitlist, and fines
- **Structured data**: MongoDB holds all live state (availability, borrow records, reservations, fines)
- **Auth**: JWT-based login for students and admins (bcrypt-hashed passwords) — every
  circulation/chat/admin action is bound to the authenticated user, never a client-supplied ID
- **Frontend**: a single-page chat UI (`static/index.html`) — aurora/glassmorphism login,
  a book-avatar assistant with idle/thinking/responding states, and search results rendered
  as tilting "book cards" — no React/build step, served directly by FastAPI

The two-store split (ChromaDB for *meaning*, MongoDB for *live facts*) is still the core
architecture decision — call it out explicitly in your Solution Blueprint doc.

---

## Prerequisites

1. **Python 3.11+** — `python --version`
2. **MongoDB Community Server** — installs as a Windows service on `localhost:27017`, starts automatically, nothing to run manually.
3. **An Anthropic API key** — console.anthropic.com → create a key.

---

## Step 1 — Open in VS Code
```powershell
cd path\to\library_ai_assistant
code .
```
Open a terminal: **Terminal → New Terminal** (PowerShell by default).

## Step 2 — Virtual environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
If activation is blocked:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Prompt should now show `(venv)`.

## Step 3 — Install dependencies
```powershell
pip install -r requirements.txt
```
First run takes a few minutes (PyTorch download for sentence-transformers).

## Step 4 — Configure environment
```powershell
copy .env.example .env
```
Paste your real key into `.env`:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```
Generate a real JWT secret and admin setup key (don't ship the placeholder values):
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Paste the output into `JWT_SECRET_KEY` in `.env`, and pick any passphrase for `ADMIN_SETUP_KEY`.

## Step 5 — Seed the database + build the vector index
```powershell
python -m app.ingest
```
Re-run this any time `data/sample_books.json` changes.

## Step 6 — Run the server
```powershell
uvicorn app.main:app --reload
```
Open **http://127.0.0.1:8000/** for the chat UI — register a student account on the "New member"
tab, then sign in. Open **http://127.0.0.1:8000/docs** for the Swagger API explorer (useful for
creating an admin account via `POST /auth/admin/register` with your `ADMIN_SETUP_KEY`).

---

## Authentication

- **Students**: register via the UI or `POST /auth/register`, then `POST /auth/login` returns a
  JWT. Every protected endpoint expects `Authorization: Bearer <token>`.
- **Admins**: `POST /auth/admin/register` requires `setup_key` to match `ADMIN_SETUP_KEY` in
  `.env` — this is what stops anyone from self-registering as admin. Then `POST /auth/admin/login`.
- **Trust boundary**: `student_id` is never accepted from the request body on any protected
  route (chat, circulation, dashboard) — it's always read from the token. See the security note
  at the top of `agent/tools.py` for why this matters for the chat agent specifically.
- Tokens expire after 1 day (`JWT_EXPIRE_MINUTES` in `config.py`).

---

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | — | Student self-registration |
| POST | `/auth/login` | — | Student login → JWT |
| POST | `/auth/admin/register` | setup key | Admin registration |
| POST | `/auth/admin/login` | — | Admin login → JWT |
| POST | `/chat` | student | Main agentic entry point (natural language, multi-turn) |
| GET | `/books/search?q=...` | — | Direct semantic search, bypassing the agent |
| GET | `/books/{book_id}/availability` | — | Live copy count + shelf location |
| GET | `/students/{student_id}/dashboard` | student (self only) | Borrowed books, due-soon, reservations, fine |
| POST | `/circulation/issue` | student | Issue a book (sets due date) |
| POST | `/circulation/return` | student | Return a book (calculates fine, frees copy, notifies waitlist) |
| POST | `/circulation/renew` | student | Renew (blocked if max renewals hit or someone's waiting) |
| POST | `/circulation/reserve` | student | Join the waitlist |
| POST | `/circulation/cancel-reservation` | student | Leave the waitlist |
| POST | `/admin/books` | admin | Add a new title (catalog + vector index) |
| PATCH | `/admin/books/copies` | admin | Adjust total copies (e.g. library buys more) |
| DELETE | `/admin/books/{book_id}` | admin | Remove a title |
| GET | `/admin/analytics/most-borrowed` | admin | Top borrowed books |
| GET | `/admin/analytics/never-borrowed` | admin | Dead stock |
| GET | `/admin/analytics/overdue` | admin | Currently overdue records |

### Try these in `/chat` (after logging in — student_id is bound to your token automatically)
```json
{"message": "I'm studying CS501 and weak in search algorithms, recommend some books", "history": []}
{"message": "I need an NLP book for tomorrow's exam, give me the best available one", "history": []}
{"message": "CS603 er jonno NLP-r boi chai", "history": []}
{"message": "Issue book B001 to student S12345", "history": []}
```
For multi-turn, take the `"history"` field from one response and pass it back into the next request.

---

## Project structure
```
library_ai_assistant/
├── app/
│   ├── api/              # FastAPI routers — thin, no business logic
│   │   ├── chat.py
│   │   ├── books.py
│   │   ├── students.py
│   │   ├── circulation.py
│   │   └── admin.py
│   ├── agent/             # the agentic loop
│   │   ├── agent.py        # tool-calling loop
│   │   ├── prompts.py      # system prompt (multi-language support lives here)
│   │   └── tools.py        # tool schemas + dispatch
│   ├── services/           # all business logic
│   │   ├── book_service.py
│   │   ├── circulation_service.py   # issue/return/renew/reserve
│   │   ├── fine_service.py
│   │   ├── recommendation_service.py # chained RAG + availability + ranking
│   │   ├── student_service.py        # dashboard aggregation
│   │   └── analytics_service.py      # admin aggregation queries
│   ├── database/
│   │   ├── mongo.py        # connection + collection handles
│   │   └── models.py       # documented collection shapes
│   ├── rag/
│   │   ├── embeddings.py   # embedding model, isolated so it's swappable
│   │   └── vector_store.py # ChromaDB indexing + semantic search
│   ├── config.py           # settings + circulation policy constants
│   ├── ingest.py            # one-time seed script
│   └── main.py               # wires all routers together
├── data/sample_books.json
├── requirements.txt
├── .env.example
└── README.md
```

## What to screenshot for your Prompt Engineering Journal / Blueprint
1. `/docs` Swagger UI — proof of a working, multi-router API
2. A `/chat` response's `tool_calls` field for a chained request (e.g. the "best available book" query) — this is your strongest agentic-AI evidence, since it shows the agent invoking `find_best_available_book`, which itself chains retrieval + availability + ranking
3. The layered folder structure itself — a genuine "why this design" talking point for the viva

## Known scope boundaries (good "Future Enhancements" bullets — don't build these, just name them)
- **Token refresh / logout server-side** — tokens are stateless JWTs valid for 1 day; there's no
  revocation list, so "logout" just deletes the local token, and a stolen token stays valid until
  it expires.
- **Voice interface** — speech-to-text in front of `/chat`.
- **Search-query logging** — "most searched subjects" analytics needs a new `search_log` collection that isn't implemented yet.
- **LangGraph** — the agent loop is hand-rolled with the raw Anthropic API for transparency/stability; swapping in `create_react_agent` (same pattern as your SentinelOps project) is a one-file change.

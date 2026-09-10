"""
config.py
---------
Single source of truth for all settings AND library policy constants.
Keeping policy numbers (fine rate, loan period, max renewals) here means
changing them for a real deployment never requires touching service logic.
"""

import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "library_assistant")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
CHROMA_COLLECTION_NAME = "library_catalog"

# Local, free, no-API-key embedding model — 384-dim, ~80MB, CPU-friendly.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# --- Library circulation policy ---
LOAN_PERIOD_DAYS = 14        # how long a book stays issued before it's due
MAX_RENEWALS = 2             # how many times a single issue can be renewed
FINE_PER_DAY = 5             # rupees charged per day overdue

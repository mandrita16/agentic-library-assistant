"""
config.py
---------
Single source of truth for all MindSync settings
and library policy constants.

Keeping policy numbers such as fine rate, loan period,
and maximum renewals here means changing them for a
real deployment never requires modifying service logic.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# Application
# ============================================================

APP_NAME = "MindSync"


# ============================================================
# MongoDB Configuration
# ============================================================

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017"
)

MONGO_DB_NAME = os.getenv(
    "MONGO_DB_NAME",
    "library_assistant"
)


# ============================================================
# Anthropic / Claude Configuration
# ============================================================

ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY",
    ""
)

CLAUDE_MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-sonnet-4-6"
)


# ============================================================
# ChromaDB Configuration
# ============================================================

CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_PERSIST_DIR",
    "./chroma_store"
)

CHROMA_COLLECTION_NAME = os.getenv(
    "CHROMA_COLLECTION_NAME",
    "library_catalog"
)


# ============================================================
# Embedding Model
# ============================================================

# Local, free, no-API-key embedding model.
# Produces 384-dimensional embeddings and is
# relatively lightweight for local/CPU usage.

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2"
)


# ============================================================
# Library Circulation Policy
# ============================================================

LOAN_PERIOD_DAYS = int(
    os.getenv("LOAN_PERIOD_DAYS", "14")
)

MAX_RENEWALS = int(
    os.getenv("MAX_RENEWALS", "2")
)

FINE_PER_DAY = float(
    os.getenv("FINE_PER_DAY", "5")
)
# ============================================================
# JWT Authentication Configuration
# ============================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    ""
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

JWT_EXPIRE_MINUTES = int(
    os.getenv("JWT_EXPIRE_MINUTES", "60")
)
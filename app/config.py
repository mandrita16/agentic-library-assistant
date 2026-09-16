"""
app/config.py
-------------
Single source of truth for MindSync application settings,
AI configuration, database configuration, authentication,
RAG configuration, and library policy constants.
"""

import os

from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()


# ============================================================
# Application
# ============================================================

APP_NAME = os.getenv(
    "APP_NAME",
    "MindSync"
)


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
# JWT Authentication Configuration
# ============================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "change-this-secret-key"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

JWT_EXPIRE_MINUTES = int(
    os.getenv(
        "JWT_EXPIRE_MINUTES",
        "60"
    )
)


# ============================================================
# Admin Authentication Configuration
# ============================================================

ADMIN_SETUP_KEY = os.getenv(
    "ADMIN_SETUP_KEY",
    ""
)


# ============================================================
# Groq / LLM Configuration
# ============================================================

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY",
    ""
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
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
# Embedding Model Configuration
# ============================================================

# Local sentence-transformer model.
# Does not require an API key.
#
# all-MiniLM-L6-v2 produces 384-dimensional embeddings
# and is lightweight enough for local development.

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2"
)


# ============================================================
# Library Circulation Policy
# ============================================================

LOAN_PERIOD_DAYS = int(
    os.getenv(
        "LOAN_PERIOD_DAYS",
        "14"
    )
)

MAX_RENEWALS = int(
    os.getenv(
        "MAX_RENEWALS",
        "2"
    )
)

FINE_PER_DAY = float(
    os.getenv(
        "FINE_PER_DAY",
        "5"
    )
)
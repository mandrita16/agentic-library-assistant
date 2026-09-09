"""
config.py
---------
Single source of truth for all settings. Every other module imports from
here instead of calling os.getenv() directly — this way, if you ever need
to change a default (e.g. switch Mongo URI, swap embedding model), you
only change it in ONE place.
"""

import os
from dotenv import load_dotenv

# Loads variables from your .env file into the environment.
# Must run before anything else tries to read os.getenv().
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "library_assistant")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"  # reasoning/generation model used by the agent

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_store")
CHROMA_COLLECTION_NAME = "library_catalog"

# Local, free, no-API-key-needed embedding model (runs on CPU fine for a
# few hundred/thousand books). 384-dim vectors, ~80MB download once.
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

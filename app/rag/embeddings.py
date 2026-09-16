"""
app/rag/embeddings.py
---------------------

Embedding generation for the MindSync RAG system.

This module is intentionally isolated from the rest of the
application so that the embedding model can be replaced without
changing the vector-store or service logic.

The same embedding function is used for:

1. Indexing library books.
2. Embedding user search queries.

This ensures that documents and queries live in the same
vector space.
"""

from sentence_transformers import SentenceTransformer

from app.config import EMBEDDING_MODEL_NAME


# ============================================================
# EMBEDDING MODEL
# ============================================================

_embedder = SentenceTransformer(
    EMBEDDING_MODEL_NAME
)


# ============================================================
# EMBEDDING FUNCTION
# ============================================================

def embed_text(text: str) -> list[float]:
    """
    Convert text into a normalized embedding vector.

    Args:
        text: Text to embed.

    Returns:
        A normalized embedding vector as a Python list.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    text = text.strip()

    if not text:
        raise ValueError("text cannot be empty.")

    embedding = _embedder.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()
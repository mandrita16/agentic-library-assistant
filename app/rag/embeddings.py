"""
rag/embeddings.py
------------------
Isolated on purpose: if you ever want to swap the embedding model (e.g.
a bigger one for better accuracy, or a multilingual one for the Bengali/
English mixed-query feature), this is the ONLY file you touch.
"""

from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL_NAME

_embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """Turns a string into a normalized 384-dim vector as a plain list (Chroma wants lists, not numpy arrays)."""
    return _embedder.encode(text, normalize_embeddings=True).tolist()

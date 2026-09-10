"""
vector_store.py
----------------
This is the "R" (Retrieval) in RAG.

We embed each book's title + description + tags into a 384-dimensional
vector using a local sentence-transformers model (free, runs on your
laptop CPU, no API key). ChromaDB stores these vectors on disk and lets
us do a similarity search: given a user's natural-language query, find
the books whose MEANING is closest — even if no keyword matches.

Example this solves that plain keyword search can't:
  Query: "something to help me understand how chatbots understand language"
  -> semantically close to "Speech and Language Processing" / NLP book,
     even though the query contains none of those exact words.
"""

import chromadb
from sentence_transformers import SentenceTransformer
from app.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL_NAME

# Loaded once at import time — loading the model per-request would be slow.
_embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

_chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_collection = _chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)


def _embed_text(text: str) -> list[float]:
    """Turns a string into a vector. .tolist() because Chroma wants plain lists, not numpy arrays."""
    return _embedder.encode(text, normalize_embeddings=True).tolist()


def build_document_text(book: dict) -> str:
    """
    Decides WHAT text actually gets embedded for a book.
    We concatenate title + subject + description + tags + course codes so
    a query can match on any of these angles (topic, course, keyword).
    """
    parts = [
        book.get("title", ""),
        book.get("subject", ""),
        book.get("description", ""),
        " ".join(book.get("tags", [])),
        " ".join(book.get("course_codes", [])),
    ]
    return " | ".join(p for p in parts if p)


def index_books(book_list: list[dict]) -> None:
    """
    Embeds every book and upserts it into ChromaDB.
    Run this once after seeding MongoDB (see ingest.py) and again any
    time the catalog changes.
    """
    ids = [b["book_id"] for b in book_list]
    documents = [build_document_text(b) for b in book_list]
    embeddings = [_embed_text(doc) for doc in documents]
    # metadatas let us filter/display results without a second DB round-trip
    metadatas = [
        {"title": b["title"], "author": b["author"], "subject": b["subject"]}
        for b in book_list
    ]

    _collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    print(f"[vector_store] Indexed {len(book_list)} books into ChromaDB.")


def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """
    The core retrieval call. Returns the top_k most semantically similar
    books to the query, each with a book_id we can then look up live
    availability for in MongoDB.
    """
    query_embedding = _embed_text(query)
    results = _collection.query(query_embeddings=[query_embedding], n_results=top_k)

    hits = []
    for i in range(len(results["ids"][0])):
        hits.append(
            {
                "book_id": results["ids"][0][i],
                "distance": results["distances"][0][i],  # lower = more similar
                "metadata": results["metadatas"][0][i],
            }
        )
    return hits

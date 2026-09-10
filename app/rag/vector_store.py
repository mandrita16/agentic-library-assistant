"""
rag/vector_store.py
--------------------
The "R" (Retrieval) in RAG. ChromaDB stores embeddings on disk; we query
it for the books whose MEANING is closest to a natural-language question
— even when no keyword overlaps.

This module deliberately knows NOTHING about live availability, fines,
or circulation. It only answers "which books are semantically relevant."
Live state always comes from database/mongo.py + services/. Keeping this
separation clean is what makes the two-store architecture explainable.
"""

import chromadb
from app.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
from app.rag.embeddings import embed_text

_chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
_collection = _chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)


def build_document_text(book: dict) -> str:
    """What text actually gets embedded — title/subject/description/tags/course codes, so a query can match on any angle."""
    parts = [
        book.get("title", ""),
        book.get("subject", ""),
        book.get("description", ""),
        " ".join(book.get("tags", [])),
        " ".join(book.get("course_codes", [])),
    ]
    return " | ".join(p for p in parts if p)


def index_books(book_list: list[dict]) -> None:
    """Embeds every book and upserts it into ChromaDB. Run via ingest.py after seeding MongoDB, or again whenever the catalog changes."""
    ids = [b["book_id"] for b in book_list]
    documents = [build_document_text(b) for b in book_list]
    embeddings = [embed_text(doc) for doc in documents]
    metadatas = [
        {"title": b["title"], "author": b["author"], "subject": b["subject"]}
        for b in book_list
    ]
    _collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
    print(f"[vector_store] Indexed {len(book_list)} books into ChromaDB.")


def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """Returns the top_k most semantically similar books (book_id + similarity distance + metadata). Live availability is looked up separately."""
    query_embedding = embed_text(query)
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

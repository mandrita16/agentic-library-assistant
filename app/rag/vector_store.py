"""
app/rag/vector_store.py
-----------------------

The retrieval layer of the MindSync RAG system.

ChromaDB stores semantic embeddings of library books and retrieves
books that are conceptually relevant to a natural-language query.

This module deliberately knows NOTHING about:

    - live availability
    - borrowing
    - reservations
    - fines
    - students

Those responsibilities belong to MongoDB and the service layer.

Architecture:

    Book
      ↓
    build_document_text()
      ↓
    embed_text()
      ↓
    ChromaDB

    User Query
      ↓
    embed_text()
      ↓
    ChromaDB semantic search
      ↓
    Relevant book IDs
      ↓
    Service layer checks live MongoDB state
"""


import chromadb

from app.config import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
)

from app.rag.embeddings import embed_text


# ============================================================
# CHROMA CONNECTION
# ============================================================

_chroma_client = chromadb.PersistentClient(
    path=CHROMA_PERSIST_DIR
)

_collection = _chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION_NAME
)


# ============================================================
# DOCUMENT PREPARATION
# ============================================================

def build_document_text(book: dict) -> str:
    """
    Build the text representation that will be embedded.

    The embedding includes multiple aspects of a book so that
    semantic search can match queries based on:

        - title
        - subject
        - description
        - tags
        - course codes

    Args:
        book: Library book dictionary.

    Returns:
        Combined searchable text.
    """

    if not isinstance(book, dict):
        raise TypeError("book must be a dictionary.")

    parts = [
        str(book.get("title", "")).strip(),
        str(book.get("subject", "")).strip(),
        str(book.get("description", "")).strip(),
        " ".join(
            str(tag).strip()
            for tag in book.get("tags", [])
            if str(tag).strip()
        ),
        " ".join(
            str(code).strip()
            for code in book.get("course_codes", [])
            if str(code).strip()
        ),
    ]

    document = " | ".join(
        part
        for part in parts
        if part
    )

    if not document:
        raise ValueError(
            "Book does not contain enough information to create "
            "an embedding."
        )

    return document


# ============================================================
# INDEXING
# ============================================================

def index_books(book_list: list[dict]) -> None:
    """
    Embed and upsert books into ChromaDB.

    Existing books with the same book_id are updated.

    Args:
        book_list: List of library book dictionaries.
    """

    if not isinstance(book_list, list):
        raise TypeError("book_list must be a list.")

    if not book_list:
        print("[vector_store] No books to index.")
        return

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for book in book_list:

        if not isinstance(book, dict):
            raise TypeError("Every book must be a dictionary.")

        book_id = str(book.get("book_id", "")).strip()

        if not book_id:
            raise ValueError(
                "Every book must contain a non-empty book_id."
            )

        document = build_document_text(book)

        ids.append(book_id)
        documents.append(document)
        embeddings.append(embed_text(document))

        metadatas.append(
            {
                "title": str(book.get("title", "")),
                "author": str(book.get("author", "")),
                "subject": str(book.get("subject", "")),
            }
        )

    _collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(
        f"[vector_store] Indexed {len(book_list)} "
        f"books into ChromaDB."
    )


# ============================================================
# SEMANTIC SEARCH
# ============================================================

def semantic_search(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve books that are semantically similar to a query.

    Lower Chroma distance means greater similarity.

    This function only performs semantic retrieval.
    It does NOT check live availability.

    Args:
        query: Natural-language search query.
        top_k: Maximum number of results.

    Returns:
        List of matching books containing:

            book_id
            distance
            metadata
    """

    if not isinstance(query, str):
        raise TypeError("query must be a string.")

    query = query.strip()

    if not query:
        raise ValueError("query cannot be empty.")

    if not isinstance(top_k, int):
        raise TypeError("top_k must be an integer.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    # No books indexed yet.
    collection_count = _collection.count()

    if collection_count == 0:
        return []

    top_k = min(
        top_k,
        collection_count,
    )

    query_embedding = embed_text(query)

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    hits = []

    for i, book_id in enumerate(ids):

        hits.append(
            {
                "book_id": book_id,
                "distance": distances[i],
                "metadata": metadatas[i],
            }
        )

    return hits
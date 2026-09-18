"""
app/rag/vector_store.py
-----------------------

ChromaDB retrieval layer for MindSync.

Responsibilities:
    - Convert books into searchable text
    - Generate embeddings
    - Store book embeddings in ChromaDB
    - Perform semantic search

ChromaDB does NOT handle:
    - availability
    - borrowing
    - returns
    - reservations
    - fines
    - students

MongoDB remains the source of truth for live library data.

Architecture:

    MongoDB Books
          |
          v
    build_document_text()
          |
          v
       Embedding
          |
          v
       ChromaDB
          |
          v
    Semantic Search
          |
          v
      book_id
          |
          v
    MongoDB lookup
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
    Build the searchable text representation of a book.

    The embedding includes:

        - title
        - subject
        - description
        - tags
        - course codes
        - moods

    Moods are important for MindSync's
    mood-based recommendation system.
    """

    if not isinstance(book, dict):
        raise TypeError(
            "book must be a dictionary."
        )

    # --------------------------------------------------------
    # Basic fields
    # --------------------------------------------------------

    title = str(
        book.get("title", "")
    ).strip()

    subject = str(
        book.get("subject", "")
    ).strip()

    description = str(
        book.get("description", "")
    ).strip()

    # --------------------------------------------------------
    # Tags
    # --------------------------------------------------------

    tags = " ".join(
        str(tag).strip()
        for tag in book.get("tags", [])
        if str(tag).strip()
    )

    # --------------------------------------------------------
    # Course codes
    # --------------------------------------------------------

    course_codes = " ".join(
        str(code).strip()
        for code in book.get("course_codes", [])
        if str(code).strip()
    )

    # --------------------------------------------------------
    # Moods
    # --------------------------------------------------------

    moods = " ".join(
        str(mood).strip()
        for mood in book.get("moods", [])
        if str(mood).strip()
    )

    # --------------------------------------------------------
    # Build searchable document
    # --------------------------------------------------------

    parts = [
        title,
        subject,
        description,
        f"Tags: {tags}" if tags else "",
        f"Course Codes: {course_codes}"
        if course_codes
        else "",
        f"Moods: {moods}"
        if moods
        else "",
    ]

    document = " | ".join(
        part
        for part in parts
        if part
    )

    if not document:
        raise ValueError(
            "Book does not contain enough information "
            "to create an embedding."
        )

    return document


# ============================================================
# INDEX BOOKS
# ============================================================

def index_books(book_list: list[dict]) -> None:
    """
    Embed and upsert books into ChromaDB.

    Existing books with the same book_id are updated.

    MongoDB remains the source of truth.

    Args:
        book_list:
            List of book dictionaries.
    """

    if not isinstance(book_list, list):
        raise TypeError(
            "book_list must be a list."
        )

    if not book_list:
        print(
            "[vector_store] No books to index."
        )
        return

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for book in book_list:

        if not isinstance(book, dict):
            raise TypeError(
                "Every book must be a dictionary."
            )

        # ----------------------------------------------------
        # Book ID
        # ----------------------------------------------------

        book_id = str(
            book.get("book_id", "")
        ).strip()

        if not book_id:
            raise ValueError(
                "Every book must contain "
                "a non-empty book_id."
            )

        # ----------------------------------------------------
        # Build document
        # ----------------------------------------------------

        document = build_document_text(book)

        # ----------------------------------------------------
        # Generate embedding
        # ----------------------------------------------------

        embedding = embed_text(
            document
        )

        # ----------------------------------------------------
        # Store data
        # ----------------------------------------------------

        ids.append(book_id)

        documents.append(
            document
        )

        embeddings.append(
            embedding
        )

        # Chroma metadata must contain
        # simple scalar values.
        metadatas.append(
            {
                "title": str(
                    book.get("title", "")
                ),

                "author": str(
                    book.get("author", "")
                ),

                "subject": str(
                    book.get("subject", "")
                ),
            }
        )

    # --------------------------------------------------------
    # Upsert into ChromaDB
    # --------------------------------------------------------

    _collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    print(
        f"[vector_store] Indexed "
        f"{len(book_list)} books into ChromaDB."
    )


# ============================================================
# SEMANTIC SEARCH
# ============================================================

def semantic_search(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve books that are semantically similar
    to a natural-language query.

    Lower Chroma distance means greater similarity.

    This function ONLY performs semantic retrieval.

    It does NOT check:

        - availability
        - borrowing
        - reservations
        - fines
        - students

    Args:
        query:
            Natural-language search query.

        top_k:
            Maximum number of results.

    Returns:
        List containing:

            book_id
            distance
            metadata
    """

    # --------------------------------------------------------
    # Validate query
    # --------------------------------------------------------

    if not isinstance(query, str):
        raise TypeError(
            "query must be a string."
        )

    query = query.strip()

    if not query:
        raise ValueError(
            "query cannot be empty."
        )

    # --------------------------------------------------------
    # Validate top_k
    # --------------------------------------------------------

    if not isinstance(top_k, int):
        raise TypeError(
            "top_k must be an integer."
        )

    if top_k < 1:
        raise ValueError(
            "top_k must be at least 1."
        )

    # --------------------------------------------------------
    # Check whether Chroma has books
    # --------------------------------------------------------

    collection_count = _collection.count()

    if collection_count == 0:
        return []

    # Never request more results
    # than the collection contains.

    top_k = min(
        top_k,
        collection_count,
    )

    # --------------------------------------------------------
    # Embed user query
    # --------------------------------------------------------

    query_embedding = embed_text(
        query
    )

    # --------------------------------------------------------
    # Query ChromaDB
    # --------------------------------------------------------

    results = _collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=top_k,
    )

    # --------------------------------------------------------
    # Extract results
    # --------------------------------------------------------

    ids = results.get(
        "ids",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    # --------------------------------------------------------
    # Build clean response
    # --------------------------------------------------------

    hits = []

    for i, book_id in enumerate(ids):

        hits.append(
            {
                "book_id": book_id,

                "distance": (
                    distances[i]
                    if i < len(distances)
                    else None
                ),

                "metadata": (
                    metadatas[i]
                    if i < len(metadatas)
                    else {}
                ),
            }
        )

    return hits


# ============================================================
# COLLECTION INFORMATION
# ============================================================

def get_collection_count() -> int:
    """
    Return the number of books currently indexed
    in ChromaDB.
    """

    return _collection.count()


# ============================================================
# CLEAR COLLECTION
# ============================================================

def clear_collection() -> None:
    """
    Delete all indexed books from the ChromaDB collection.

    Useful when rebuilding the complete vector index.
    """

    global _collection

    _chroma_client.delete_collection(
        name=CHROMA_COLLECTION_NAME
    )

    _collection = _chroma_client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME
    )

    print(
        "[vector_store] ChromaDB collection cleared."
    )
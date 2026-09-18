"""
app/ingest.py
-------------

Initializes the MindSync library catalog.

Run this once during setup, and again whenever
data/sample_books.json changes.

Pipeline:

    sample_books.json
           │
           ├──────────────→ MongoDB
           │                 structured catalog
           │
           └──────────────→ ChromaDB
                             semantic/vector index

Usage from the project root:

    python -m app.ingest
"""

import json
from pathlib import Path

from app.services.book_service import seed_books
from app.rag.vector_store import index_books


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BOOKS_FILE = (
    PROJECT_ROOT
    / "data"
    / "sample_books.json"
)


# ============================================================
# CATALOG VALIDATION
# ============================================================

def validate_books(books: list[dict]) -> None:
    """
    Validate the book catalog before inserting it into MongoDB
    and indexing it into ChromaDB.

    Checks:

        - catalog must be a list
        - every item must be a dictionary
        - every book must have a book_id
        - book IDs must be unique
        - every book must have a title
    """

    if not isinstance(books, list):
        raise ValueError(
            "sample_books.json must contain "
            "a JSON list of books."
        )

    if not books:
        raise ValueError(
            "sample_books.json contains no books."
        )

    book_ids = set()

    for index, book in enumerate(
        books,
        start=1,
    ):

        # ----------------------------------------------------
        # Check object
        # ----------------------------------------------------

        if not isinstance(book, dict):
            raise ValueError(
                f"Book #{index} must be a JSON object."
            )

        # ----------------------------------------------------
        # Check book_id
        # ----------------------------------------------------

        book_id = str(
            book.get("book_id", "")
        ).strip()

        if not book_id:
            raise ValueError(
                f"Book #{index} is missing book_id."
            )

        # ----------------------------------------------------
        # Check duplicate IDs
        # ----------------------------------------------------

        if book_id in book_ids:
            raise ValueError(
                f"Duplicate book_id found: {book_id}"
            )

        book_ids.add(book_id)

        # ----------------------------------------------------
        # Check title
        # ----------------------------------------------------

        title = str(
            book.get("title", "")
        ).strip()

        if not title:
            raise ValueError(
                f"Book {book_id} is missing title."
            )

    print(
        f"[ingest] Catalog validation successful: "
        f"{len(books)} books."
    )


# ============================================================
# LOAD BOOK CATALOG
# ============================================================

def load_books() -> list[dict]:
    """
    Load the book catalog from sample_books.json.

    Returns:
        List of validated books.
    """

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not BOOKS_FILE.exists():
        raise FileNotFoundError(
            f"Book catalog not found: {BOOKS_FILE}"
        )

    # --------------------------------------------------------
    # Load JSON
    # --------------------------------------------------------

    try:

        with BOOKS_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            books = json.load(file)

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"Invalid JSON in {BOOKS_FILE}: {exc}"
        ) from exc

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_books(books)

    return books


# ============================================================
# INGESTION
# ============================================================

def main() -> None:
    """
    Load, validate, seed, and index the library catalog.
    """

    # --------------------------------------------------------
    # Load books
    # --------------------------------------------------------

    books = load_books()

    print(
        f"[ingest] Loaded {len(books)} books "
        f"from {BOOKS_FILE}"
    )

    # --------------------------------------------------------
    # Seed MongoDB
    # --------------------------------------------------------

    print(
        "[ingest] Seeding MongoDB..."
    )

    seed_books(books)

    print(
        "[ingest] MongoDB catalog seeded successfully."
    )

    # --------------------------------------------------------
    # Build ChromaDB vector index
    # --------------------------------------------------------

    print(
        "[ingest] Building ChromaDB vector index..."
    )

    index_books(books)

    print(
        "[ingest] ChromaDB vector index built successfully."
    )

    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    print(
        "[ingest] Ingestion complete."
    )

    print(
        f"[ingest] Total books processed: {len(books)}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
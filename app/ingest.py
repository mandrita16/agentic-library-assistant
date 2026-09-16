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
# INGESTION
# ============================================================


def main() -> None:
    """Load, seed, and index the library catalog."""

    # --------------------------------------------------------
    # Validate input file
    # --------------------------------------------------------

    if not BOOKS_FILE.exists():
        raise FileNotFoundError(
            f"Book catalog not found: {BOOKS_FILE}"
        )

    # --------------------------------------------------------
    # Load JSON catalog
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
    # Validate catalog
    # --------------------------------------------------------

    if not isinstance(books, list):
        raise ValueError(
            "sample_books.json must contain a JSON list of books."
        )

    if not books:
        print("[ingest] Warning: catalog is empty.")
        return

    print(
        f"[ingest] Loaded {len(books)} books "
        f"from {BOOKS_FILE}"
    )

    # --------------------------------------------------------
    # Seed MongoDB
    # --------------------------------------------------------

    seed_books(books)

    print(
        "[ingest] MongoDB catalog seeded successfully."
    )

    # --------------------------------------------------------
    # Build ChromaDB vector index
    # --------------------------------------------------------

    index_books(books)

    print(
        "[ingest] ChromaDB vector index built successfully."
    )

    print(
        "[ingest] Ingestion complete."
    )


# ============================================================
# ENTRY POINT
# ============================================================


if __name__ == "__main__":
    main()
"""
ingest.py
---------
Run this ONCE (and again whenever sample_books.json changes) to:
  1. Load the sample catalog JSON
  2. Seed it into MongoDB (structured data)
  3. Embed it into ChromaDB (vector data)

Usage (from the project root, with your venv active):
    python -m app.ingest
"""

import json
from app.database import seed_books
from app.vector_store import index_books


def main():
    with open("data/sample_books.json", "r", encoding="utf-8") as f:
        books = json.load(f)

    print(f"[ingest] Loaded {len(books)} books from data/sample_books.json")

    seed_books(books)
    print("[ingest] MongoDB seeded.")

    index_books(books)
    print("[ingest] ChromaDB vector index built. Ingestion complete.")


if __name__ == "__main__":
    main()

"""
database/mongo.py
------------------
Just the connection + raw collection handles. No business logic here —
that lives in app/services/. This file's only job is "how do I reach
MongoDB and which collections exist."

Collections:
  books          - catalog + live availability counts
  students       - student profile, running fine balance, hashed password
  admins         - librarian/admin accounts, hashed password
  borrow_records - one doc per issue (issue_date, due_date, return_date,
                   status, renewal_count)
  reservations   - waitlist entries when a book has zero copies free
"""

from pymongo import MongoClient

from app.config import MONGO_URI, MONGO_DB_NAME


_client = MongoClient(MONGO_URI)
_db = _client[MONGO_DB_NAME]


books_collection = _db["books"]
students_collection = _db["students"]
admins_collection = _db["admins"]
borrow_records_collection = _db["borrow_records"]
reservations_collection = _db["reservations"]
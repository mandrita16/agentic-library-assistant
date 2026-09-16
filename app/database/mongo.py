"""
app/database/mongo.py
---------------------

MongoDB connection and raw collection handles.

This module contains NO business logic.

Business logic belongs in app/services/.

Collections
-----------

books
    Library catalog and live availability counts.

students
    Student profiles, password hashes, and outstanding fines.

admins
    Librarian/admin accounts and password hashes.

borrow_records
    One document per borrowing transaction.

reservations
    Waitlist entries for unavailable books.
"""

from pymongo import MongoClient

from app.config import MONGO_URI, MONGO_DB_NAME


# ============================================================
# CONNECTION
# ============================================================

_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
)

_db = _client[MONGO_DB_NAME]


# ============================================================
# COLLECTIONS
# ============================================================

books_collection = _db["books"]

students_collection = _db["students"]

admins_collection = _db["admins"]

borrow_records_collection = _db["borrow_records"]

reservations_collection = _db["reservations"]


# ============================================================
# INDEXES
# ============================================================

# ------------------------------------------------------------
# Books
# ------------------------------------------------------------

books_collection.create_index(
    "book_id",
    unique=True,
)


# ------------------------------------------------------------
# Students
# ------------------------------------------------------------

students_collection.create_index(
    "student_id",
    unique=True,
)


# ------------------------------------------------------------
# Admins
# ------------------------------------------------------------

admins_collection.create_index(
    "admin_id",
    unique=True,
)


# ------------------------------------------------------------
# Borrow Records
# ------------------------------------------------------------

borrow_records_collection.create_index(
    "record_id",
    unique=True,
)

# Useful for:
# "Show all books borrowed by this student"
borrow_records_collection.create_index(
    [
        ("student_id", 1),
        ("status", 1),
    ]
)

# Useful for:
# "Check whether this book is currently issued"
borrow_records_collection.create_index(
    [
        ("book_id", 1),
        ("status", 1),
    ]
)


# ------------------------------------------------------------
# Reservations
# ------------------------------------------------------------

reservations_collection.create_index(
    "reservation_id",
    unique=True,
)

# Useful for:
# Finding the next student in a book's waitlist.
reservations_collection.create_index(
    [
        ("book_id", 1),
        ("status", 1),
        ("queue_position", 1),
    ]
)

# Useful for:
# Finding a student's active reservations.
reservations_collection.create_index(
    [
        ("student_id", 1),
        ("status", 1),
    ]
)


# ============================================================
# CONNECTION CHECK
# ============================================================

def check_database_connection() -> bool:
    """
    Check whether MongoDB is reachable.

    Returns:
        True  -> MongoDB responded successfully.
        False -> MongoDB could not be reached.
    """

    try:
        _client.admin.command("ping")
        return True

    except Exception:
        return False
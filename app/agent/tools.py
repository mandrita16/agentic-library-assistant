"""
app/agent/tools.py
------------------

LangGraph tools used by the MindSync agent.

IMPORTANT:
- This file DEFINES TOOLS.
- It must NOT import TOOLS from itself.
- Business logic remains inside app/services/.
"""

from typing import Optional

from langchain_core.tools import tool

from app.services import book_service
from app.services import circulation_service


# ============================================================
# BOOK SEARCH
# ============================================================

@tool
def search_catalog(query: str, top_k: int = 5) -> list:
    """
    Search the library catalog for books matching a query.

    Use this when a student wants to find books, subjects,
    authors, or learning resources.
    """

    if not isinstance(query, str):
        return []

    query = query.strip()

    if not query:
        return []

    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 5

    top_k = max(1, min(top_k, 20))

    try:
        return book_service.search_books(
            query=query,
            top_k=top_k,
        )

    except TypeError:
        # Compatibility fallback in case the service uses
        # a positional argument instead of top_k.
        try:
            return book_service.search_books(
                query,
                top_k,
            )
        except Exception as exc:
            return {
                "error": f"Book search failed: {str(exc)}"
            }

    except Exception as exc:
        return {
            "error": f"Book search failed: {str(exc)}"
        }


# ============================================================
# BOOK AVAILABILITY
# ============================================================

@tool
def check_book_availability(book_id: str) -> dict:
    """
    Check the current availability of a book.
    """

    if not isinstance(book_id, str) or not book_id.strip():
        return {
            "error": "A valid book_id is required."
        }

    try:
        # Use the existing service function if available.
        if hasattr(book_service, "get_book"):
            book = book_service.get_book(book_id.strip())

        elif hasattr(book_service, "get_book_by_id"):
            book = book_service.get_book_by_id(book_id.strip())

        else:
            return {
                "error": "Book availability service is unavailable."
            }

        if not book:
            return {
                "error": f"Book {book_id} was not found."
            }

        return {
            "book_id": book.get("book_id", book_id),
            "title": book.get("title"),
            "total_copies": book.get("total_copies"),
            "available_copies": book.get("available_copies"),
        }

    except Exception as exc:
        return {
            "error": f"Could not check availability: {str(exc)}"
        }


# ============================================================
# BORROW / ISSUE
# ============================================================

@tool
def borrow_book(book_id: str, student_id: str) -> dict:
    """
    Borrow/issue an available book to the authenticated student.
    """

    if not book_id or not student_id:
        return {
            "success": False,
            "error": "book_id and student_id are required."
        }

    try:
        # Existing circulation service.
        if hasattr(circulation_service, "issue_book"):
            result = circulation_service.issue_book(
                book_id=book_id,
                student_id=student_id,
            )

        elif hasattr(circulation_service, "issue"):
            result = circulation_service.issue(
                book_id=book_id,
                student_id=student_id,
            )

        else:
            return {
                "success": False,
                "error": "Borrow service is unavailable."
            }

        return _normalize_result(result)

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# RETURN
# ============================================================

@tool
def return_book(book_id: str, student_id: str) -> dict:
    """
    Return a book currently borrowed by the student.
    """

    if not book_id or not student_id:
        return {
            "success": False,
            "error": "book_id and student_id are required."
        }

    try:
        if hasattr(circulation_service, "return_book"):
            result = circulation_service.return_book(
                book_id=book_id,
                student_id=student_id,
            )

        elif hasattr(circulation_service, "return_book_for_student"):
            result = circulation_service.return_book_for_student(
                book_id=book_id,
                student_id=student_id,
            )

        elif hasattr(circulation_service, "return_book_transaction"):
            result = circulation_service.return_book_transaction(
                book_id=book_id,
                student_id=student_id,
            )

        else:
            return {
                "success": False,
                "error": "Return service is unavailable."
            }

        return _normalize_result(result)

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# RENEW
# ============================================================

@tool
def renew_book(book_id: str, student_id: str) -> dict:
    """
    Renew a book borrowed by the student.
    """

    if not book_id or not student_id:
        return {
            "success": False,
            "error": "book_id and student_id are required."
        }

    try:
        if hasattr(circulation_service, "renew_book"):
            result = circulation_service.renew_book(
                book_id=book_id,
                student_id=student_id,
            )

        elif hasattr(circulation_service, "renew"):
            result = circulation_service.renew(
                book_id=book_id,
                student_id=student_id,
            )

        else:
            return {
                "success": False,
                "error": "Renewal service is unavailable."
            }

        return _normalize_result(result)

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# RESERVE
# ============================================================

@tool
def reserve_book(book_id: str, student_id: str) -> dict:
    """
    Reserve a book that is currently unavailable.
    """

    if not book_id or not student_id:
        return {
            "success": False,
            "error": "book_id and student_id are required."
        }

    try:
        if hasattr(circulation_service, "reserve_book"):
            result = circulation_service.reserve_book(
                book_id=book_id,
                student_id=student_id,
            )

        elif hasattr(circulation_service, "reserve"):
            result = circulation_service.reserve(
                book_id=book_id,
                student_id=student_id,
            )

        else:
            return {
                "success": False,
                "error": "Reservation service is unavailable."
            }

        return _normalize_result(result)

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# CANCEL RESERVATION
# ============================================================

@tool
def cancel_reservation(
    book_id: str,
    student_id: str,
) -> dict:
    """
    Cancel an active reservation for a book.
    """

    if not book_id or not student_id:
        return {
            "success": False,
            "error": "book_id and student_id are required."
        }

    try:
        if hasattr(
            circulation_service,
            "cancel_reservation",
        ):
            result = circulation_service.cancel_reservation(
                book_id=book_id,
                student_id=student_id,
            )

        elif hasattr(
            circulation_service,
            "cancel_book_reservation",
        ):
            result = circulation_service.cancel_book_reservation(
                book_id=book_id,
                student_id=student_id,
            )

        else:
            return {
                "success": False,
                "error": "Cancellation service is unavailable."
            }

        return _normalize_result(result)

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# STUDENT BORROWINGS
# ============================================================

@tool
def get_student_borrowings(student_id: str) -> list | dict:
    """
    Get books currently borrowed by the authenticated student.
    """

    if not student_id:
        return {
            "error": "student_id is required."
        }

    try:
        if hasattr(
            circulation_service,
            "get_student_borrowings",
        ):
            result = circulation_service.get_student_borrowings(
                student_id
            )

        elif hasattr(
            circulation_service,
            "get_borrowed_books",
        ):
            result = circulation_service.get_borrowed_books(
                student_id
            )

        elif hasattr(
            circulation_service,
            "get_active_borrowings",
        ):
            result = circulation_service.get_active_borrowings(
                student_id
            )

        else:
            return {
                "error": "Borrowing lookup service is unavailable."
            }

        return result

    except Exception as exc:
        return {
            "error": str(exc)
        }


# ============================================================
# STUDENT FINES
# ============================================================

@tool
def get_student_fines(student_id: str) -> dict | list:
    """
    Get outstanding fines and overdue information for a student.
    """

    if not student_id:
        return {
            "error": "student_id is required."
        }

    try:
        if hasattr(
            circulation_service,
            "get_student_fines",
        ):
            return circulation_service.get_student_fines(
                student_id
            )

        if hasattr(
            circulation_service,
            "get_fines",
        ):
            return circulation_service.get_fines(
                student_id
            )

        if hasattr(
            circulation_service,
            "get_student_dashboard",
        ):
            dashboard = circulation_service.get_student_dashboard(
                student_id
            )

            if isinstance(dashboard, dict):
                return {
                    "student_id": student_id,
                    "fines": dashboard.get(
                        "fines",
                        dashboard.get("outstanding_fines", 0),
                    ),
                    "overdue": dashboard.get(
                        "overdue",
                        [],
                    ),
                }

        return {
            "error": "Fine lookup service is unavailable."
        }

    except Exception as exc:
        return {
            "error": str(exc)
        }


# ============================================================
# HELPER
# ============================================================

def _normalize_result(result):
    """
    Convert service results into a tool-friendly structure.

    This prevents LangGraph/tool responses from becoming
    unexpected strings where dictionaries are expected.
    """

    if result is None:
        return {
            "success": False,
            "error": "The service returned no result."
        }

    if isinstance(result, dict):
        return result

    if isinstance(result, list):
        return {
            "success": True,
            "data": result,
        }

    if isinstance(result, str):
        return {
            "success": True,
            "message": result,
        }

    return {
        "success": True,
        "data": str(result),
    }


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS = [
    search_catalog,
    check_book_availability,
    borrow_book,
    return_book,
    renew_book,
    reserve_book,
    cancel_reservation,
    get_student_borrowings,
    get_student_fines,
]
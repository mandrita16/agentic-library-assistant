"""
database/models.py
-------------------
MongoDB is schemaless, so nothing here is enforced at the DB level — but
writing the shape down explicitly is genuinely useful for your viva and
for anyone else on the team reading the code. Think of these as
"documentation types", not real ORM models.

BOOK
{
  book_id: str, title: str, author: str, isbn: str, subject: str,
  course_codes: [str], description: str, shelf_location: str,
  total_copies: int, available_copies: int, tags: [str]
}

STUDENT
{
  student_id: str, name: str, department: str,
  outstanding_fine: float   # rupees, running total
}

BORROW_RECORD
{
  record_id: str, book_id: str, student_id: str,
  issue_date: datetime, due_date: datetime, return_date: datetime | None,
  status: "issued" | "returned" | "overdue",
  renewal_count: int
}

RESERVATION
{
  reservation_id: str, book_id: str, student_id: str,
  status: "waiting" | "ready" | "cancelled" | "fulfilled",
  queue_position: int, created_at: datetime
}
"""

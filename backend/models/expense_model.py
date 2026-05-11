"""Expense tracking database helpers."""

from __future__ import annotations

from typing import Any

from utils.helpers import get_db_connection, now_iso, row_to_dict


def create_expense_table() -> None:
    """Create the expenses table."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                vendor_name TEXT NOT NULL,
                gstin TEXT,
                category TEXT,
                expense_date TEXT NOT NULL,
                taxable_amount REAL NOT NULL,
                gst_rate REAL NOT NULL,
                gst_amount REAL NOT NULL,
                total REAL NOT NULL,
                payment_mode TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_expenses_owner ON expenses(owner_user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date)")
        connection.commit()


def list_expenses(owner_user_id: int | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    """Return expenses scoped to a user unless include_all is true."""
    query = "SELECT * FROM expenses"
    params: list[Any] = []
    if owner_user_id is not None and not include_all:
        query += " WHERE owner_user_id = ?"
        params.append(owner_user_id)
    query += " ORDER BY expense_date DESC, id DESC"
    with get_db_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_expense_by_id(expense_id: int, owner_user_id: int | None = None, include_all: bool = False) -> dict[str, Any] | None:
    """Return one expense by ID."""
    query = "SELECT * FROM expenses WHERE id = ?"
    params: list[Any] = [expense_id]
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
    return row_to_dict(row)


def insert_expense(expense: dict[str, Any]) -> dict[str, Any]:
    """Insert an expense."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO expenses (
                owner_user_id, vendor_name, gstin, category, expense_date,
                taxable_amount, gst_rate, gst_amount, total, payment_mode,
                notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                expense.get("owner_user_id"),
                expense["vendor_name"],
                expense.get("gstin", ""),
                expense.get("category", ""),
                expense["expense_date"],
                expense["taxable_amount"],
                expense["gst_rate"],
                expense["gst_amount"],
                expense["total"],
                expense.get("payment_mode", ""),
                expense.get("notes", ""),
                now,
                now,
            ),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM expenses WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row) or {}


def update_expense_record(expense_id: int, expense: dict[str, Any]) -> dict[str, Any] | None:
    """Update an expense."""
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE expenses
            SET vendor_name = ?, gstin = ?, category = ?, expense_date = ?,
                taxable_amount = ?, gst_rate = ?, gst_amount = ?, total = ?,
                payment_mode = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                expense["vendor_name"],
                expense.get("gstin", ""),
                expense.get("category", ""),
                expense["expense_date"],
                expense["taxable_amount"],
                expense["gst_rate"],
                expense["gst_amount"],
                expense["total"],
                expense.get("payment_mode", ""),
                expense.get("notes", ""),
                now_iso(),
                expense_id,
            ),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    return row_to_dict(row)


def delete_expense_record(expense_id: int, owner_user_id: int | None = None, include_all: bool = False) -> bool:
    """Delete an expense."""
    query = "DELETE FROM expenses WHERE id = ?"
    params: list[Any] = [expense_id]
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    with get_db_connection() as connection:
        cursor = connection.execute(query, params)
        connection.commit()
        return cursor.rowcount > 0


"""Payment reminder history model."""

from __future__ import annotations

from typing import Any

from utils.helpers import get_db_connection, now_iso


def create_reminder_table() -> None:
    """Create reminder history table."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reminder_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                invoice_id INTEGER,
                invoice_number TEXT,
                recipient_email TEXT,
                status TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_reminder_owner ON reminder_logs(owner_user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_reminder_invoice ON reminder_logs(invoice_id)")
        connection.commit()


def insert_reminder_log(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert reminder history entry."""
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO reminder_logs (
                owner_user_id, invoice_id, invoice_number, recipient_email, status, message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("owner_user_id"),
                payload.get("invoice_id"),
                payload.get("invoice_number", ""),
                payload.get("recipient_email", ""),
                payload.get("status", ""),
                payload.get("message", ""),
                now_iso(),
            ),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM reminder_logs WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_reminder_logs(owner_user_id: int | None = None, include_all: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    """List reminder history."""
    query = "SELECT * FROM reminder_logs"
    params: list[Any] = []
    if owner_user_id is not None and not include_all:
        query += " WHERE owner_user_id = ?"
        params.append(owner_user_id)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_db_connection() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]

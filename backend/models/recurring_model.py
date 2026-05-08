"""Recurring invoice database helpers."""

from __future__ import annotations

import json
from typing import Any

from utils.helpers import get_db_connection, now_iso, row_to_dict


def create_recurring_table() -> None:
    """Create recurring invoice table."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                name TEXT NOT NULL,
                client_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                frequency TEXT NOT NULL DEFAULT 'monthly',
                next_run_date TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                last_generated_invoice_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_recurring_owner ON recurring_invoices(owner_user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_recurring_next_run ON recurring_invoices(next_run_date)")
        connection.commit()


def insert_recurring(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a recurring invoice profile."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO recurring_invoices (
                owner_user_id, name, client_name, payload, frequency, next_run_date,
                active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("owner_user_id"),
                payload["name"],
                payload["client_name"],
                json.dumps(payload["payload"], ensure_ascii=True),
                payload.get("frequency", "monthly"),
                payload["next_run_date"],
                int(bool(payload.get("active", True))),
                now,
                now,
            ),
        )
        connection.commit()
    return get_recurring_by_id(int(cursor.lastrowid)) or {}


def list_recurring(owner_user_id: int | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    """List recurring invoice profiles."""
    query = "SELECT * FROM recurring_invoices"
    params: tuple[Any, ...] = ()
    if owner_user_id is not None and not include_all:
        query += " WHERE owner_user_id = ?"
        params = (owner_user_id,)
    query += " ORDER BY id DESC"
    with get_db_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_normalize_recurring(dict(row)) for row in rows]


def get_recurring_by_id(recurring_id: int, owner_user_id: int | None = None, include_all: bool = False) -> dict[str, Any] | None:
    """Return one recurring invoice profile."""
    query = "SELECT * FROM recurring_invoices WHERE id = ?"
    params: tuple[Any, ...] = (recurring_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (recurring_id, owner_user_id)
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
    value = row_to_dict(row)
    return _normalize_recurring(value) if value else None


def update_recurring_record(recurring_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Update a recurring invoice profile."""
    current = get_recurring_by_id(recurring_id)
    if current is None:
        return None
    merged = {**current, **payload}
    stored_payload = merged.get("payload", {})
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE recurring_invoices
            SET name = ?, client_name = ?, payload = ?, frequency = ?,
                next_run_date = ?, active = ?, last_generated_invoice_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                merged["name"],
                merged["client_name"],
                json.dumps(stored_payload, ensure_ascii=True),
                merged.get("frequency", "monthly"),
                merged["next_run_date"],
                int(bool(merged.get("active", True))),
                merged.get("last_generated_invoice_id"),
                now_iso(),
                recurring_id,
            ),
        )
        connection.commit()
    return get_recurring_by_id(recurring_id)


def delete_recurring_record(recurring_id: int, owner_user_id: int | None = None, include_all: bool = False) -> bool:
    """Delete recurring invoice profile."""
    query = "DELETE FROM recurring_invoices WHERE id = ?"
    params: tuple[Any, ...] = (recurring_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (recurring_id, owner_user_id)
    with get_db_connection() as connection:
        cursor = connection.execute(query, params)
        connection.commit()
    return cursor.rowcount > 0


def due_recurring_profiles(today: str, owner_user_id: int | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    """Return active recurring profiles due on or before a date."""
    query = "SELECT * FROM recurring_invoices WHERE active = 1 AND next_run_date <= ?"
    params: list[Any] = [today]
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    with get_db_connection() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    return [_normalize_recurring(dict(row)) for row in rows]


def _normalize_recurring(row: dict[str, Any]) -> dict[str, Any]:
    """Decode JSON payload."""
    try:
        row["payload"] = json.loads(row.get("payload") or "{}")
    except json.JSONDecodeError:
        row["payload"] = {}
    row["active"] = bool(row.get("active", True))
    return row

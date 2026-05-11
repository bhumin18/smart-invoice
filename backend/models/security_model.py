"""Security and login activity database helpers."""

from __future__ import annotations

from typing import Any

from utils.helpers import get_db_connection, now_iso


def create_security_tables() -> None:
    """Create security event tables and indexes."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                event_type TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                success INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_auth_events_user ON auth_events(user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_auth_events_created ON auth_events(created_at)")
        connection.commit()


def insert_auth_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert one authentication/security event."""
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO auth_events (
                user_id, username, event_type, ip_address, user_agent, success, message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("user_id"),
                payload.get("username", ""),
                payload.get("event_type", ""),
                payload.get("ip_address", ""),
                payload.get("user_agent", ""),
                int(bool(payload.get("success", False))),
                payload.get("message", ""),
                now_iso(),
            ),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM auth_events WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def list_auth_events(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent authentication/security events."""
    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM auth_events ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]

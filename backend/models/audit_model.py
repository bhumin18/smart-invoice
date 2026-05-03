"""Audit log database helpers."""

from __future__ import annotations

import json
from typing import Any

from utils.helpers import get_db_connection, now_iso


def create_audit_table() -> None:
    """Create the audit log table and indexes."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                actor_user_id INTEGER,
                actor_username TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_owner ON audit_logs(owner_user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at)")
        connection.commit()


def insert_audit_log(
    *,
    owner_user_id: int | None,
    actor_user_id: int | None,
    actor_username: str,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: dict[str, Any] | None = None,
) -> None:
    """Insert one audit log entry."""
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_logs (
                owner_user_id, actor_user_id, actor_username, action,
                entity_type, entity_id, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_user_id,
                actor_user_id,
                actor_username,
                action,
                entity_type,
                entity_id,
                json.dumps(details or {}, ensure_ascii=True),
                now_iso(),
            ),
        )
        connection.commit()


def get_audit_logs(
    *,
    entity_type: str | None = None,
    entity_id: int | None = None,
    owner_user_id: int | None = None,
    include_all: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return audit log entries."""
    clauses: list[str] = []
    params: list[Any] = []
    if entity_type:
        clauses.append("entity_type = ?")
        params.append(entity_type)
    if entity_id is not None:
        clauses.append("entity_id = ?")
        params.append(entity_id)
    if owner_user_id is not None and not include_all:
        clauses.append("owner_user_id = ?")
        params.append(owner_user_id)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM audit_logs
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, int(limit)),
        ).fetchall()
    logs = [dict(row) for row in rows]
    for log in logs:
        try:
            log["details"] = json.loads(log.get("details") or "{}")
        except json.JSONDecodeError:
            log["details"] = {}
    return logs

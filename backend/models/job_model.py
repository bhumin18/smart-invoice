"""Background job log database helpers."""

from __future__ import annotations

import json
from typing import Any

from utils.helpers import get_db_connection, now_iso


def create_job_table() -> None:
    """Create background job log table."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS job_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                result TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_job_logs_name ON job_logs(job_name)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_job_logs_started ON job_logs(started_at)")
        connection.commit()


def insert_job_log(job_name: str, status: str, message: str = "", result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Insert one background job log."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO job_logs (job_name, status, message, result, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (job_name, status, message, json.dumps(result or {}, ensure_ascii=True), now, now),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM job_logs WHERE id = ?", (cursor.lastrowid,)).fetchone()
    log = dict(row)
    try:
        log["result"] = json.loads(log.get("result") or "{}")
    except json.JSONDecodeError:
        log["result"] = {}
    return log


def list_job_logs(limit: int = 100) -> list[dict[str, Any]]:
    """Return recent background job logs."""
    with get_db_connection() as connection:
        rows = connection.execute("SELECT * FROM job_logs ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    logs = [dict(row) for row in rows]
    for log in logs:
        try:
            log["result"] = json.loads(log.get("result") or "{}")
        except json.JSONDecodeError:
            log["result"] = {}
    return logs

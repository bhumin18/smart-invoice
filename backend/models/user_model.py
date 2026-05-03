"""User account database helpers."""

from __future__ import annotations

from typing import Any

from werkzeug.security import generate_password_hash

from config import get_config
from utils.helpers import get_db_connection, now_iso, row_to_dict


def create_user_table() -> None:
    """Create users table and seed the configured admin user."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                active INTEGER NOT NULL DEFAULT 1,
                reset_token TEXT,
                reset_expires_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        existing = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        extra_columns = {
            "can_create_invoices": "INTEGER NOT NULL DEFAULT 1",
            "can_manage_company": "INTEGER NOT NULL DEFAULT 1",
            "can_export_data": "INTEGER NOT NULL DEFAULT 1",
        }
        for column, definition in extra_columns.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
        count = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
        if int(count) == 0:
            now = now_iso()
            connection.execute(
                """
                INSERT INTO users (username, email, password_hash, role, active, created_at, updated_at)
                VALUES (?, ?, ?, 'admin', 1, ?, ?)
                """,
                (
                    str(get_config("auth.admin_username", "admin")),
                    str(get_config("auth.admin_email", "admin@example.com")),
                    generate_password_hash(str(get_config("auth.admin_password", "admin123"))),
                    now,
                    now,
                ),
            )
        connection.commit()


def user_count() -> int:
    """Return number of user accounts."""
    with get_db_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()
    return int(row["total"] if row else 0)


def get_user_by_username(username: str) -> dict[str, Any] | None:
    """Return one user by username."""
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE lower(username) = lower(?)",
            (username.strip(),),
        ).fetchone()
    return row_to_dict(row)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    """Return one user by email."""
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE lower(email) = lower(?)",
            (email.strip(),),
        ).fetchone()
    return row_to_dict(row)


def insert_user(username: str, email: str, password: str, role: str = "admin") -> dict[str, Any]:
    """Create a user with a hashed password."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username, email, password_hash, role, active,
                can_create_invoices, can_manage_company, can_export_data,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 1, 1, 1, 1, ?, ?)
            """,
            (username.strip(), email.strip(), generate_password_hash(password), role, now, now),
        )
        connection.commit()
    with get_db_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row) or {}


def list_users() -> list[dict[str, Any]]:
    """Return users for admin management."""
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id, username, email, role, active,
                can_create_invoices, can_manage_company, can_export_data,
                created_at, updated_at
            FROM users
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Return one user by ID."""
    with get_db_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_dict(row)


def update_user_record(user_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Update admin-managed user fields."""
    current = get_user_by_id(user_id)
    if current is None:
        return None
    merged = {**current, **payload}
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET role = ?, active = ?, can_create_invoices = ?, can_manage_company = ?,
                can_export_data = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(merged.get("role") or "user"),
                int(bool(merged.get("active", True))),
                int(bool(merged.get("can_create_invoices", True))),
                int(bool(merged.get("can_manage_company", True))),
                int(bool(merged.get("can_export_data", True))),
                now_iso(),
                user_id,
            ),
        )
        connection.commit()
    return get_user_by_id(user_id)


def set_reset_token(user_id: int, token: str, expires_at: str) -> None:
    """Persist password reset token for a user."""
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE users SET reset_token = ?, reset_expires_at = ?, updated_at = ? WHERE id = ?",
            (token, expires_at, now_iso(), user_id),
        )
        connection.commit()


def get_user_by_reset_token(token: str) -> dict[str, Any] | None:
    """Return user by reset token."""
    with get_db_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE reset_token = ?", (token,)).fetchone()
    return row_to_dict(row)


def update_password(user_id: int, password: str) -> None:
    """Update a user's password and clear reset token."""
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, reset_token = NULL, reset_expires_at = NULL, updated_at = ?
            WHERE id = ?
            """,
            (generate_password_hash(password), now_iso(), user_id),
        )
        connection.commit()

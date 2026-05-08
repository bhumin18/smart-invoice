"""Application settings database helpers."""

from __future__ import annotations

from typing import Any

from config import get_config
from utils.helpers import get_db_connection, now_iso


def create_settings_table() -> None:
    """Create app settings table."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def get_setting(key: str, default: Any = None) -> str:
    """Return a stored setting value."""
    with get_db_connection() as connection:
        row = connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return str(default if default is not None else "")
    return str(row["value"])


def set_setting(key: str, value: Any) -> None:
    """Persist a setting value."""
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, str(value), now_iso()),
        )
        connection.commit()


def registration_enabled() -> bool:
    """Return whether self-registration is enabled."""
    configured = bool(get_config("auth.allow_registration", True))
    value = get_setting("auth.allow_registration", "true" if configured else "false")
    return value.strip().lower() in {"1", "true", "yes", "on"}

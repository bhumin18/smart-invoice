"""Client master database helpers."""

from __future__ import annotations

from typing import Any

from utils.helpers import get_db_connection, now_iso, row_to_dict


def _ensure_client_columns(connection) -> None:
    """Add ownership columns to existing client tables."""
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(clients)").fetchall()}
    if "owner_user_id" not in existing:
        connection.execute("ALTER TABLE clients ADD COLUMN owner_user_id INTEGER")
    admin = connection.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    if admin is not None:
        connection.execute("UPDATE clients SET owner_user_id = ? WHERE owner_user_id IS NULL", (admin["id"],))


def create_client_table() -> None:
    """Create the client master table."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                name TEXT NOT NULL,
                gstin TEXT,
                address TEXT,
                state TEXT,
                phone TEXT,
                email TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_client_columns(connection)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_clients_gstin ON clients(gstin)")
        connection.commit()


def list_clients(search: str = "", owner_user_id: int | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    """Return clients, optionally searched by name, GSTIN, phone, or email."""
    params: tuple[Any, ...] = ()
    where_sql = ""
    clauses: list[str] = []
    params_list: list[Any] = []
    if search.strip():
        term = f"%{search.strip()}%"
        clauses.append("(name LIKE ? OR gstin LIKE ? OR phone LIKE ? OR email LIKE ?)")
        params_list.extend([term, term, term, term])
    if owner_user_id is not None and not include_all:
        clauses.append("owner_user_id = ?")
        params_list.append(owner_user_id)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM clients {where_sql} ORDER BY name COLLATE NOCASE",
            tuple(params_list),
        ).fetchall()
    return [dict(row) for row in rows]


def get_client_by_id(client_id: int, owner_user_id: int | None = None, include_all: bool = False) -> dict[str, Any] | None:
    """Return one client by ID."""
    query = "SELECT * FROM clients WHERE id = ?"
    params: tuple[Any, ...] = (client_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (client_id, owner_user_id)
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
    return row_to_dict(row)


def insert_client(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a client and return the created record."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO clients (owner_user_id, name, gstin, address, state, phone, email, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("owner_user_id"),
                payload["name"],
                payload.get("gstin", ""),
                payload.get("address", ""),
                payload.get("state", ""),
                payload.get("phone", ""),
                payload.get("email", ""),
                payload.get("notes", ""),
                now,
                now,
            ),
        )
        connection.commit()
    return get_client_by_id(int(cursor.lastrowid)) or {}


def update_client_record(client_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Update a client and return the updated record."""
    current = get_client_by_id(client_id)
    if current is None:
        return None
    merged = {**current, **payload}
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE clients
            SET name = ?, gstin = ?, address = ?, state = ?, phone = ?, email = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                merged["name"],
                merged.get("gstin", ""),
                merged.get("address", ""),
                merged.get("state", ""),
                merged.get("phone", ""),
                merged.get("email", ""),
                merged.get("notes", ""),
                now_iso(),
                client_id,
            ),
        )
        connection.commit()
    return get_client_by_id(client_id)


def delete_client_record(client_id: int, owner_user_id: int | None = None, include_all: bool = False) -> bool:
    """Delete a client by ID."""
    query = "DELETE FROM clients WHERE id = ?"
    params: tuple[Any, ...] = (client_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (client_id, owner_user_id)
    with get_db_connection() as connection:
        cursor = connection.execute(query, params)
        connection.commit()
    return cursor.rowcount > 0

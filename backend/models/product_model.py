"""Product and service master database helpers."""

from __future__ import annotations

from typing import Any

from utils.helpers import get_db_connection, now_iso, row_to_dict


def _ensure_product_columns(connection) -> None:
    """Add ownership columns to existing product tables."""
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(products)").fetchall()}
    if "owner_user_id" not in existing:
        connection.execute("ALTER TABLE products ADD COLUMN owner_user_id INTEGER")
    admin = connection.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    if admin is not None:
        connection.execute("UPDATE products SET owner_user_id = ? WHERE owner_user_id IS NULL", (admin["id"],))


def create_product_table() -> None:
    """Create the product/service master table."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                hsn_sac TEXT,
                price REAL NOT NULL DEFAULT 0,
                gst_rate REAL NOT NULL DEFAULT 18,
                unit TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_product_columns(connection)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_products_hsn_sac ON products(hsn_sac)")
        connection.commit()


def list_products(
    search: str = "",
    active_only: bool = False,
    owner_user_id: int | None = None,
    include_all: bool = False,
) -> list[dict[str, Any]]:
    """Return products/services, optionally searched and filtered by active state."""
    clauses: list[str] = []
    params: list[Any] = []
    if search.strip():
        clauses.append("(name LIKE ? OR hsn_sac LIKE ? OR description LIKE ?)")
        term = f"%{search.strip()}%"
        params.extend([term, term, term])
    if active_only:
        clauses.append("active = 1")
    if owner_user_id is not None and not include_all:
        clauses.append("owner_user_id = ?")
        params.append(owner_user_id)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM products {where_sql} ORDER BY name COLLATE NOCASE",
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def get_product_by_id(product_id: int, owner_user_id: int | None = None, include_all: bool = False) -> dict[str, Any] | None:
    """Return one product/service by ID."""
    query = "SELECT * FROM products WHERE id = ?"
    params: tuple[Any, ...] = (product_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (product_id, owner_user_id)
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
    return row_to_dict(row)


def insert_product(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a product/service and return the created record."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO products (owner_user_id, name, description, hsn_sac, price, gst_rate, unit, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("owner_user_id"),
                payload["name"],
                payload.get("description", ""),
                payload.get("hsn_sac", ""),
                payload.get("price", 0.0),
                payload.get("gst_rate", 18.0),
                payload.get("unit", ""),
                int(bool(payload.get("active", True))),
                now,
                now,
            ),
        )
        connection.commit()
    return get_product_by_id(int(cursor.lastrowid)) or {}


def update_product_record(product_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Update a product/service and return the updated record."""
    current = get_product_by_id(product_id)
    if current is None:
        return None
    merged = {**current, **payload}
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE products
            SET name = ?, description = ?, hsn_sac = ?, price = ?, gst_rate = ?, unit = ?, active = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                merged["name"],
                merged.get("description", ""),
                merged.get("hsn_sac", ""),
                merged.get("price", 0.0),
                merged.get("gst_rate", 18.0),
                merged.get("unit", ""),
                int(bool(merged.get("active", True))),
                now_iso(),
                product_id,
            ),
        )
        connection.commit()
    return get_product_by_id(product_id)


def delete_product_record(product_id: int, owner_user_id: int | None = None, include_all: bool = False) -> bool:
    """Delete a product/service by ID."""
    query = "DELETE FROM products WHERE id = ?"
    params: tuple[Any, ...] = (product_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (product_id, owner_user_id)
    with get_db_connection() as connection:
        cursor = connection.execute(query, params)
        connection.commit()
    return cursor.rowcount > 0

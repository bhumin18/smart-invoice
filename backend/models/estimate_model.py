"""Estimate and quotation database helpers."""

from __future__ import annotations

from typing import Any

from utils.helpers import get_db_connection, now_iso, row_to_dict


def create_estimate_tables() -> None:
    """Create estimate-related tables."""
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                estimate_number TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_gstin TEXT,
                client_address TEXT,
                date TEXT NOT NULL,
                valid_until TEXT,
                supply_type TEXT NOT NULL DEFAULT 'intrastate',
                place_of_supply TEXT,
                subtotal REAL NOT NULL,
                gst_amount REAL NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                notes TEXT,
                converted_invoice_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS estimate_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                estimate_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                description TEXT,
                hsn_sac TEXT,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                gst_rate REAL NOT NULL,
                line_subtotal REAL NOT NULL,
                line_gst REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (estimate_id) REFERENCES estimates(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_estimates_owner ON estimates(owner_user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_estimates_number ON estimates(estimate_number)")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_estimates_owner_number ON estimates(owner_user_id, estimate_number)"
        )
        connection.commit()


def _estimate_items(connection, estimate_id: int) -> list[dict[str, Any]]:
    """Return items for an estimate."""
    rows = connection.execute("SELECT * FROM estimate_items WHERE estimate_id = ? ORDER BY id", (estimate_id,)).fetchall()
    return [dict(row) for row in rows]


def _row_with_items(connection, row) -> dict[str, Any] | None:
    """Convert estimate row and attach items."""
    estimate = row_to_dict(row)
    if estimate:
        estimate["items"] = _estimate_items(connection, int(estimate["id"]))
    return estimate


def list_estimates(owner_user_id: int | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    """Return estimates scoped to a user unless include_all is true."""
    query = "SELECT * FROM estimates"
    params: list[Any] = []
    if owner_user_id is not None and not include_all:
        query += " WHERE owner_user_id = ?"
        params.append(owner_user_id)
    query += " ORDER BY date DESC, id DESC"
    with get_db_connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [_row_with_items(connection, row) or {} for row in rows]


def get_estimate_by_id(estimate_id: int, owner_user_id: int | None = None, include_all: bool = False) -> dict[str, Any] | None:
    """Return one estimate by ID."""
    query = "SELECT * FROM estimates WHERE id = ?"
    params: list[Any] = [estimate_id]
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
        return _row_with_items(connection, row)


def estimate_number_exists(number: str, owner_user_id: int | None = None, exclude_estimate_id: int | None = None) -> bool:
    """Return whether an estimate number already exists for a user."""
    query = "SELECT id FROM estimates WHERE estimate_number = ?"
    params: list[Any] = [number]
    if owner_user_id is not None:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    if exclude_estimate_id is not None:
        query += " AND id != ?"
        params.append(exclude_estimate_id)
    with get_db_connection() as connection:
        return connection.execute(query, params).fetchone() is not None


def next_estimate_number(owner_user_id: int | None = None) -> str:
    """Return the next estimate number for a user."""
    query = "SELECT estimate_number FROM estimates"
    params: list[Any] = []
    if owner_user_id is not None:
        query += " WHERE owner_user_id = ?"
        params.append(owner_user_id)
    query += " ORDER BY id DESC LIMIT 1"
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
    if not row:
        return "QT-0001"
    suffix = str(row["estimate_number"]).split("-")[-1]
    try:
        return f"QT-{int(suffix) + 1:04d}"
    except ValueError:
        return "QT-0001"


def insert_estimate(estimate: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    """Insert estimate with items."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO estimates (
                owner_user_id, estimate_number, client_name, client_gstin, client_address,
                date, valid_until, supply_type, place_of_supply, subtotal, gst_amount,
                total, status, notes, converted_invoice_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                estimate.get("owner_user_id"),
                estimate["estimate_number"],
                estimate["client_name"],
                estimate.get("client_gstin", ""),
                estimate.get("client_address", ""),
                estimate["date"],
                estimate.get("valid_until", ""),
                estimate.get("supply_type", "intrastate"),
                estimate.get("place_of_supply", ""),
                estimate["subtotal"],
                estimate["gst_amount"],
                estimate["total"],
                estimate.get("status", "draft"),
                estimate.get("notes", ""),
                estimate.get("converted_invoice_id"),
                now,
                now,
            ),
        )
        estimate_id = int(cursor.lastrowid)
        _replace_items(connection, estimate_id, items)
        connection.commit()
        row = connection.execute("SELECT * FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
        return _row_with_items(connection, row) or {}


def update_estimate_record(estimate_id: int, estimate: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Update estimate and replace items."""
    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE estimates
            SET estimate_number = ?, client_name = ?, client_gstin = ?, client_address = ?,
                date = ?, valid_until = ?, supply_type = ?, place_of_supply = ?,
                subtotal = ?, gst_amount = ?, total = ?, status = ?, notes = ?,
                converted_invoice_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                estimate["estimate_number"],
                estimate["client_name"],
                estimate.get("client_gstin", ""),
                estimate.get("client_address", ""),
                estimate["date"],
                estimate.get("valid_until", ""),
                estimate.get("supply_type", "intrastate"),
                estimate.get("place_of_supply", ""),
                estimate["subtotal"],
                estimate["gst_amount"],
                estimate["total"],
                estimate.get("status", "draft"),
                estimate.get("notes", ""),
                estimate.get("converted_invoice_id"),
                now_iso(),
                estimate_id,
            ),
        )
        _replace_items(connection, estimate_id, items)
        connection.commit()
        row = connection.execute("SELECT * FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
        return _row_with_items(connection, row)


def mark_estimate_converted(estimate_id: int, invoice_id: int) -> dict[str, Any] | None:
    """Mark estimate as converted."""
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE estimates SET status = 'converted', converted_invoice_id = ?, updated_at = ? WHERE id = ?",
            (invoice_id, now_iso(), estimate_id),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM estimates WHERE id = ?", (estimate_id,)).fetchone()
        return _row_with_items(connection, row)


def delete_estimate_record(estimate_id: int, owner_user_id: int | None = None, include_all: bool = False) -> bool:
    """Delete an estimate."""
    query = "DELETE FROM estimates WHERE id = ?"
    params: list[Any] = [estimate_id]
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params.append(owner_user_id)
    with get_db_connection() as connection:
        cursor = connection.execute(query, params)
        connection.commit()
        return cursor.rowcount > 0


def _replace_items(connection, estimate_id: int, items: list[dict[str, Any]]) -> None:
    """Replace estimate items."""
    connection.execute("DELETE FROM estimate_items WHERE estimate_id = ?", (estimate_id,))
    for item in items:
        connection.execute(
            """
            INSERT INTO estimate_items (
                estimate_id, item_name, description, hsn_sac, quantity, price,
                gst_rate, line_subtotal, line_gst, line_total
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                estimate_id,
                item["item_name"],
                item.get("description", ""),
                item.get("hsn_sac", ""),
                item["quantity"],
                item["price"],
                item["gst_rate"],
                item["line_subtotal"],
                item["line_gst"],
                item["line_total"],
            ),
        )


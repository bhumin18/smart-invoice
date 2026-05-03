"""Invoice and invoice item database model helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from utils.helpers import get_db_connection, now_iso, row_to_dict


INVOICE_COLUMNS = {
    "owner_user_id": "INTEGER",
    "payment_terms": "TEXT",
    "amount_paid": "REAL NOT NULL DEFAULT 0",
    "balance_due": "REAL NOT NULL DEFAULT 0",
    "void_reason": "TEXT",
    "voided_at": "TEXT",
}


def _ensure_invoice_columns(connection: sqlite3.Connection) -> None:
    """Add newly supported invoice columns to existing databases."""
    existing = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(invoices)").fetchall()
    }
    for column, definition in INVOICE_COLUMNS.items():
        if column not in existing:
            connection.execute(f"ALTER TABLE invoices ADD COLUMN {column} {definition}")
    admin = connection.execute(
        "SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
    ).fetchone()
    if admin is not None and "owner_user_id" in {
        row["name"] for row in connection.execute("PRAGMA table_info(invoices)").fetchall()
    }:
        connection.execute(
            "UPDATE invoices SET owner_user_id = ? WHERE owner_user_id IS NULL",
            (admin["id"],),
        )


def _migrate_invoice_table_if_needed(connection: sqlite3.Connection) -> None:
    """Remove legacy global invoice_number unique constraint for multi-user series."""
    table = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'invoices'"
    ).fetchone()
    if table is None or "invoice_number TEXT NOT NULL UNIQUE" not in str(table["sql"]):
        return
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute(
        """
        CREATE TABLE invoices_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER,
            invoice_number TEXT NOT NULL,
            client_name TEXT NOT NULL,
            client_gstin TEXT,
            client_address TEXT,
            date TEXT NOT NULL,
            due_date TEXT,
            supply_type TEXT NOT NULL DEFAULT 'intrastate',
            place_of_supply TEXT,
            subtotal REAL NOT NULL,
            gst_amount REAL NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'sent',
            payment_terms TEXT,
            amount_paid REAL NOT NULL DEFAULT 0,
            balance_due REAL NOT NULL DEFAULT 0,
            notes TEXT,
            pdf_path TEXT,
            void_reason TEXT,
            voided_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(invoices)").fetchall()}
    admin = connection.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    owner_expr = "owner_user_id" if "owner_user_id" in existing else str(admin["id"] if admin else 1)

    def col(name: str, fallback: str) -> str:
        return name if name in existing else fallback

    connection.execute(
        f"""
        INSERT INTO invoices_new (
            id, owner_user_id, invoice_number, client_name, client_gstin, client_address,
            date, due_date, supply_type, place_of_supply, subtotal, gst_amount,
            total, status, payment_terms, amount_paid, balance_due, notes, pdf_path,
            void_reason, voided_at, created_at, updated_at
        )
        SELECT
            id,
            COALESCE({owner_expr}, ?),
            invoice_number,
            client_name,
            {col('client_gstin', "''")},
            {col('client_address', "''")},
            date,
            {col('due_date', "''")},
            {col('supply_type', "'intrastate'")},
            {col('place_of_supply', "''")},
            subtotal,
            gst_amount,
            total,
            {col('status', "'sent'")},
            {col('payment_terms', "''")},
            {col('amount_paid', "0")},
            {col('balance_due', 'total')},
            {col('notes', "''")},
            {col('pdf_path', "''")},
            {col('void_reason', "''")},
            {col('voided_at', "''")},
            created_at,
            updated_at
        FROM invoices
        """,
        (admin["id"] if admin else 1,),
    )
    connection.execute("DROP TABLE invoices")
    connection.execute("ALTER TABLE invoices_new RENAME TO invoices")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.commit()


def create_invoice_tables() -> None:
    """Create invoice-related tables."""
    with get_db_connection() as connection:
        _migrate_invoice_table_if_needed(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id INTEGER,
                invoice_number TEXT NOT NULL UNIQUE,
                client_name TEXT NOT NULL,
                client_gstin TEXT,
                client_address TEXT,
                date TEXT NOT NULL,
                due_date TEXT,
                supply_type TEXT NOT NULL DEFAULT 'intrastate',
                place_of_supply TEXT,
                subtotal REAL NOT NULL,
                gst_amount REAL NOT NULL,
                total REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'sent',
                payment_terms TEXT,
                amount_paid REAL NOT NULL DEFAULT 0,
                balance_due REAL NOT NULL DEFAULT 0,
                notes TEXT,
                pdf_path TEXT,
                void_reason TEXT,
                voided_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_invoice_columns(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                description TEXT,
                hsn_sac TEXT,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                gst_rate REAL NOT NULL,
                line_subtotal REAL NOT NULL,
                line_gst REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_mode TEXT NOT NULL,
                reference TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoices_invoice_number ON invoices(invoice_number)"
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_owner_invoice_number ON invoices(owner_user_id, invoice_number)"
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(date)")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_payments_invoice_id ON invoice_payments(invoice_id)"
        )
        connection.commit()


def insert_invoice(invoice: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    """Insert an invoice and its line items in one transaction."""
    now = now_iso()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO invoices (
                owner_user_id, invoice_number, client_name, client_gstin, client_address,
                date, due_date, supply_type, place_of_supply, subtotal, gst_amount,
                total, status, payment_terms, amount_paid, balance_due, notes,
                pdf_path, void_reason, voided_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice.get("owner_user_id"),
                invoice["invoice_number"],
                invoice["client_name"],
                invoice.get("client_gstin", ""),
                invoice.get("client_address", ""),
                invoice["date"],
                invoice.get("due_date", ""),
                invoice.get("supply_type", "intrastate"),
                invoice.get("place_of_supply", ""),
                invoice["subtotal"],
                invoice["gst_amount"],
                invoice["total"],
                invoice.get("status", "sent"),
                invoice.get("payment_terms", ""),
                invoice.get("amount_paid", 0.0),
                invoice.get("balance_due", invoice["total"]),
                invoice.get("notes", ""),
                invoice.get("pdf_path", ""),
                invoice.get("void_reason", ""),
                invoice.get("voided_at", ""),
                now,
                now,
            ),
        )
        invoice_id = cursor.lastrowid
        for item in items:
            connection.execute(
                """
                INSERT INTO invoice_items (
                    invoice_id, item_name, description, hsn_sac, quantity,
                    price, gst_rate, line_subtotal, line_gst, line_total
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
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
        connection.commit()
    return get_invoice_by_id(int(invoice_id)) or {}


def get_invoices(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return invoices without line items, optionally filtered."""
    filters = filters or {}
    clauses: list[str] = []
    params: list[Any] = []
    if filters.get("status"):
        clauses.append("lower(status) = lower(?)")
        params.append(str(filters["status"]).strip())
    if filters.get("client"):
        clauses.append("lower(client_name) LIKE lower(?)")
        params.append(f"%{str(filters['client']).strip()}%")
    if filters.get("search"):
        clauses.append("(lower(invoice_number) LIKE lower(?) OR lower(client_name) LIKE lower(?))")
        term = f"%{str(filters['search']).strip()}%"
        params.extend([term, term])
    if filters.get("date_from"):
        clauses.append("date >= ?")
        params.append(str(filters["date_from"]))
    if filters.get("date_to"):
        clauses.append("date <= ?")
        params.append(str(filters["date_to"]))
    if filters.get("owner_user_id") and not filters.get("include_all"):
        clauses.append("owner_user_id = ?")
        params.append(int(filters["owner_user_id"]))
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_db_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM invoices {where_sql} ORDER BY id DESC",
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def get_invoice_summary(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return high-level invoice totals for the dashboard."""
    filters = filters or {}
    where_sql = ""
    params: tuple[Any, ...] = ()
    if filters.get("owner_user_id") and not filters.get("include_all"):
        where_sql = "WHERE owner_user_id = ?"
        params = (int(filters["owner_user_id"]),)
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS invoice_count,
                COALESCE(SUM(CASE WHEN lower(status) != 'void' THEN total ELSE 0 END), 0) AS total_sales,
                COALESCE(SUM(CASE WHEN lower(status) != 'void' THEN gst_amount ELSE 0 END), 0) AS total_gst,
                COALESCE(SUM(CASE WHEN lower(status) != 'void' THEN balance_due ELSE 0 END), 0) AS balance_due,
                COALESCE(SUM(CASE WHEN lower(status) = 'paid' THEN total ELSE 0 END), 0) AS paid_sales,
                COALESCE(SUM(CASE WHEN lower(status) = 'void' THEN 1 ELSE 0 END), 0) AS void_count
            FROM invoices
            """ + where_sql,
            params,
        ).fetchone()
    return dict(row) if row else {}


def invoice_number_exists(
    invoice_number: str,
    exclude_invoice_id: int | None = None,
    owner_user_id: int | None = None,
    include_all: bool = False,
) -> bool:
    """Return whether an invoice number is already used."""
    query = "SELECT id FROM invoices WHERE lower(invoice_number) = lower(?)"
    params: tuple[Any, ...] = (invoice_number.strip(),)
    if exclude_invoice_id is not None:
        query += " AND id != ?"
        params = (invoice_number.strip(), exclude_invoice_id)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (*params, owner_user_id)
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
    return row is not None


def replace_invoice(invoice_id: int, invoice: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Replace invoice header fields and line items in one transaction."""
    with get_db_connection() as connection:
        exists = connection.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if exists is None:
            return None
        connection.execute(
            """
            UPDATE invoices
            SET invoice_number = ?, client_name = ?, client_gstin = ?, client_address = ?, date = ?,
                due_date = ?, supply_type = ?, place_of_supply = ?, subtotal = ?,
                gst_amount = ?, total = ?, status = ?, payment_terms = ?,
                amount_paid = ?, balance_due = ?, notes = ?, void_reason = ?,
                voided_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                invoice["invoice_number"],
                invoice["client_name"],
                invoice.get("client_gstin", ""),
                invoice.get("client_address", ""),
                invoice["date"],
                invoice.get("due_date", ""),
                invoice.get("supply_type", "intrastate"),
                invoice.get("place_of_supply", ""),
                invoice["subtotal"],
                invoice["gst_amount"],
                invoice["total"],
                invoice.get("status", "sent"),
                invoice.get("payment_terms", ""),
                invoice.get("amount_paid", 0.0),
                invoice.get("balance_due", invoice["total"]),
                invoice.get("notes", ""),
                invoice.get("void_reason", ""),
                invoice.get("voided_at", ""),
                now_iso(),
                invoice_id,
            ),
        )
        connection.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        for item in items:
            connection.execute(
                """
                INSERT INTO invoice_items (
                    invoice_id, item_name, description, hsn_sac, quantity,
                    price, gst_rate, line_subtotal, line_gst, line_total
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
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
        connection.commit()
    return get_invoice_by_id(invoice_id)


def delete_invoice(invoice_id: int, owner_user_id: int | None = None, include_all: bool = False) -> bool:
    """Delete an invoice and cascade its line items."""
    query = "DELETE FROM invoices WHERE id = ?"
    params: tuple[Any, ...] = (invoice_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (invoice_id, owner_user_id)
    with get_db_connection() as connection:
        cursor = connection.execute(query, params)
        connection.commit()
        return cursor.rowcount > 0


def get_invoice_items(invoice_id: int) -> list[dict[str, Any]]:
    """Return all line items for an invoice."""
    with get_db_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY id",
            (invoice_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_invoice_payments(invoice_id: int) -> list[dict[str, Any]]:
    """Return all recorded payments for an invoice."""
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id AS payment_id,
                payment_date AS date,
                amount,
                payment_mode AS mode,
                reference,
                notes,
                created_at
            FROM invoice_payments
            WHERE invoice_id = ?
            ORDER BY id DESC
            """,
            (invoice_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_invoice_payment_by_id(invoice_id: int, payment_id: int) -> dict[str, Any] | None:
    """Return one payment for an invoice."""
    with get_db_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id AS payment_id,
                invoice_id,
                payment_date AS date,
                amount,
                payment_mode AS mode,
                reference,
                notes,
                created_at
            FROM invoice_payments
            WHERE invoice_id = ? AND id = ?
            """,
            (invoice_id, payment_id),
        ).fetchone()
    return row_to_dict(row)


def get_invoice_by_id(invoice_id: int, owner_user_id: int | None = None, include_all: bool = False) -> dict[str, Any] | None:
    """Return one invoice with nested line items."""
    query = "SELECT * FROM invoices WHERE id = ?"
    params: tuple[Any, ...] = (invoice_id,)
    if owner_user_id is not None and not include_all:
        query += " AND owner_user_id = ?"
        params = (invoice_id, owner_user_id)
    with get_db_connection() as connection:
        row = connection.execute(query, params).fetchone()
    invoice = row_to_dict(row)
    if invoice is None:
        return None
    invoice["items"] = get_invoice_items(invoice_id)
    invoice["payments"] = get_invoice_payments(invoice_id)
    return invoice


def update_invoice_pdf_path(invoice_id: int, pdf_path: str) -> dict[str, Any] | None:
    """Persist the generated PDF path for an invoice."""
    with get_db_connection() as connection:
        connection.execute(
            "UPDATE invoices SET pdf_path = ?, updated_at = ? WHERE id = ?",
            (pdf_path, now_iso(), invoice_id),
        )
        connection.commit()
    return get_invoice_by_id(invoice_id)


def insert_invoice_payment(
    invoice_id: int,
    payment_date: str,
    amount: float,
    payment_mode: str,
    reference: str = "",
    notes: str = "",
) -> None:
    """Store a payment against an invoice."""
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO invoice_payments (
                invoice_id, payment_date, amount, payment_mode, reference, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (invoice_id, payment_date, amount, payment_mode, reference, notes, now_iso()),
        )
        connection.commit()


def get_invoice_rows_for_period(month: int, year: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return invoices with items for a month and year."""
    filters = filters or {}
    owner_sql = ""
    params: list[Any] = [month, year]
    if filters.get("owner_user_id") and not filters.get("include_all"):
        owner_sql = " AND i.owner_user_id = ?"
        params.append(int(filters["owner_user_id"]))
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT i.*, ii.item_name, ii.gst_rate, ii.line_subtotal, ii.line_gst, ii.line_total
            FROM invoices i
            JOIN invoice_items ii ON ii.invoice_id = i.id
            WHERE CAST(strftime('%m', i.date) AS INTEGER) = ?
              AND CAST(strftime('%Y', i.date) AS INTEGER) = ?
              AND lower(i.status) != 'void'
              """ + owner_sql + """
            ORDER BY i.date, i.invoice_number, ii.id
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]

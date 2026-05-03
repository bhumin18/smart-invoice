"""Company settings database model helpers."""

from __future__ import annotations

from typing import Any

from utils.helpers import get_db_connection, now_iso, row_to_dict


DEFAULT_COMPANY = {
    "name": "Your Business Name",
    "legal_name": "",
    "gstin": "",
    "pan": "",
    "address": "",
    "state": "",
    "phone": "",
    "email": "",
    "website": "",
    "bank_name": "",
    "bank_account_name": "",
    "bank_account_number": "",
    "bank_ifsc": "",
    "upi_id": "",
    "logo_path": "",
    "invoice_prefix": "INV",
    "current_number": 0,
    "invoice_number_padding": 4,
    "currency_symbol": "Rs.",
    "default_payment_terms": "Due within 15 days",
    "terms_and_conditions": "Please make the payment by the due date.",
    "authorized_signatory_name": "",
    "signature_path": "",
}

COMPANY_COLUMNS = {
    "owner_user_id": "INTEGER",
    "legal_name": "TEXT",
    "pan": "TEXT",
    "state": "TEXT",
    "website": "TEXT",
    "invoice_number_padding": "INTEGER NOT NULL DEFAULT 4",
    "currency_symbol": "TEXT NOT NULL DEFAULT 'Rs.'",
    "default_payment_terms": "TEXT",
    "terms_and_conditions": "TEXT",
    "authorized_signatory_name": "TEXT",
    "signature_path": "TEXT",
}


def _ensure_company_columns(connection) -> None:
    """Add newly supported company setting columns to existing databases."""
    existing = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(company)").fetchall()
    }
    for column, definition in COMPANY_COLUMNS.items():
        if column not in existing:
            connection.execute(f"ALTER TABLE company ADD COLUMN {column} {definition}")
    admin = connection.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    if admin is not None:
        connection.execute("UPDATE company SET owner_user_id = ? WHERE owner_user_id IS NULL", (admin["id"],))


def _migrate_company_table_if_needed(connection) -> None:
    """Remove legacy singleton CHECK constraint so each user can have a company row."""
    table = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'company'"
    ).fetchone()
    if table is None or "CHECK (id = 1)" not in str(table["sql"]):
        return
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute(
        """
        CREATE TABLE company_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER,
            name TEXT NOT NULL,
            legal_name TEXT,
            gstin TEXT,
            pan TEXT,
            address TEXT,
            state TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            bank_name TEXT,
            bank_account_name TEXT,
            bank_account_number TEXT,
            bank_ifsc TEXT,
            upi_id TEXT,
            logo_path TEXT,
            invoice_prefix TEXT NOT NULL DEFAULT 'INV',
            current_number INTEGER NOT NULL DEFAULT 0,
            invoice_number_padding INTEGER NOT NULL DEFAULT 4,
            currency_symbol TEXT NOT NULL DEFAULT 'Rs.',
            default_payment_terms TEXT,
            terms_and_conditions TEXT,
            authorized_signatory_name TEXT,
            signature_path TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    existing = {row["name"] for row in connection.execute("PRAGMA table_info(company)").fetchall()}
    admin = connection.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
    owner_expr = "owner_user_id" if "owner_user_id" in existing else str(admin["id"] if admin else 1)
    connection.execute(
        f"""
        INSERT INTO company_new (
            id, owner_user_id, name, legal_name, gstin, pan, address, state, phone, email,
            website, bank_name, bank_account_name, bank_account_number, bank_ifsc, upi_id,
            logo_path, invoice_prefix, current_number, invoice_number_padding,
            currency_symbol, default_payment_terms, terms_and_conditions,
            authorized_signatory_name, signature_path, created_at, updated_at
        )
        SELECT
            id,
            COALESCE({owner_expr}, ?),
            name, legal_name, gstin, pan, address, state, phone, email,
            website, bank_name, bank_account_name, bank_account_number, bank_ifsc, upi_id,
            logo_path, invoice_prefix, current_number, invoice_number_padding,
            currency_symbol, default_payment_terms, terms_and_conditions,
            authorized_signatory_name, signature_path, created_at, updated_at
        FROM company
        """,
        (admin["id"] if admin else 1,),
    )
    connection.execute("DROP TABLE company")
    connection.execute("ALTER TABLE company_new RENAME TO company")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.commit()


def create_company_table() -> None:
    """Create and seed the company settings table."""
    with get_db_connection() as connection:
        _migrate_company_table_if_needed(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS company (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                owner_user_id INTEGER,
                name TEXT NOT NULL,
                legal_name TEXT,
                gstin TEXT,
                pan TEXT,
                address TEXT,
                state TEXT,
                phone TEXT,
                email TEXT,
                website TEXT,
                bank_name TEXT,
                bank_account_name TEXT,
                bank_account_number TEXT,
                bank_ifsc TEXT,
                upi_id TEXT,
                logo_path TEXT,
                invoice_prefix TEXT NOT NULL DEFAULT 'INV',
                current_number INTEGER NOT NULL DEFAULT 0,
                invoice_number_padding INTEGER NOT NULL DEFAULT 4,
                currency_symbol TEXT NOT NULL DEFAULT 'Rs.',
                default_payment_terms TEXT,
                terms_and_conditions TEXT,
                authorized_signatory_name TEXT,
                signature_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_company_columns(connection)
        exists = connection.execute("SELECT id FROM company WHERE id = 1").fetchone()
        if exists is None:
            now = now_iso()
            connection.execute(
                """
                INSERT INTO company (
                    id, owner_user_id, name, legal_name, gstin, pan, address, state, phone, email,
                    website, bank_name,
                    bank_account_name, bank_account_number, bank_ifsc, upi_id,
                    logo_path, invoice_prefix, current_number, invoice_number_padding,
                    currency_symbol, default_payment_terms, terms_and_conditions,
                    authorized_signatory_name, signature_path,
                    created_at, updated_at
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    DEFAULT_COMPANY["name"],
                    DEFAULT_COMPANY["legal_name"],
                    DEFAULT_COMPANY["gstin"],
                    DEFAULT_COMPANY["pan"],
                    DEFAULT_COMPANY["address"],
                    DEFAULT_COMPANY["state"],
                    DEFAULT_COMPANY["phone"],
                    DEFAULT_COMPANY["email"],
                    DEFAULT_COMPANY["website"],
                    DEFAULT_COMPANY["bank_name"],
                    DEFAULT_COMPANY["bank_account_name"],
                    DEFAULT_COMPANY["bank_account_number"],
                    DEFAULT_COMPANY["bank_ifsc"],
                    DEFAULT_COMPANY["upi_id"],
                    DEFAULT_COMPANY["logo_path"],
                    DEFAULT_COMPANY["invoice_prefix"],
                    DEFAULT_COMPANY["current_number"],
                    DEFAULT_COMPANY["invoice_number_padding"],
                    DEFAULT_COMPANY["currency_symbol"],
                    DEFAULT_COMPANY["default_payment_terms"],
                    DEFAULT_COMPANY["terms_and_conditions"],
                    DEFAULT_COMPANY["authorized_signatory_name"],
                    DEFAULT_COMPANY["signature_path"],
                    now,
                    now,
                ),
            )
        connection.commit()


def get_company(owner_user_id: int | None = None) -> dict[str, Any]:
    """Return the singleton company settings record."""
    with get_db_connection() as connection:
        if owner_user_id is not None:
            row = connection.execute("SELECT * FROM company WHERE owner_user_id = ?", (owner_user_id,)).fetchone()
        else:
            row = connection.execute("SELECT * FROM company ORDER BY id LIMIT 1").fetchone()
        if row is None and owner_user_id is not None:
            now = now_iso()
            connection.execute(
                """
                INSERT INTO company (
                    owner_user_id, name, legal_name, gstin, pan, address, state, phone, email,
                    website, bank_name, bank_account_name, bank_account_number, bank_ifsc, upi_id,
                    logo_path, invoice_prefix, current_number, invoice_number_padding,
                    currency_symbol, default_payment_terms, terms_and_conditions,
                    authorized_signatory_name, signature_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    owner_user_id,
                    DEFAULT_COMPANY["name"],
                    DEFAULT_COMPANY["legal_name"],
                    DEFAULT_COMPANY["gstin"],
                    DEFAULT_COMPANY["pan"],
                    DEFAULT_COMPANY["address"],
                    DEFAULT_COMPANY["state"],
                    DEFAULT_COMPANY["phone"],
                    DEFAULT_COMPANY["email"],
                    DEFAULT_COMPANY["website"],
                    DEFAULT_COMPANY["bank_name"],
                    DEFAULT_COMPANY["bank_account_name"],
                    DEFAULT_COMPANY["bank_account_number"],
                    DEFAULT_COMPANY["bank_ifsc"],
                    DEFAULT_COMPANY["upi_id"],
                    DEFAULT_COMPANY["logo_path"],
                    DEFAULT_COMPANY["invoice_prefix"],
                    DEFAULT_COMPANY["current_number"],
                    DEFAULT_COMPANY["invoice_number_padding"],
                    DEFAULT_COMPANY["currency_symbol"],
                    DEFAULT_COMPANY["default_payment_terms"],
                    DEFAULT_COMPANY["terms_and_conditions"],
                    DEFAULT_COMPANY["authorized_signatory_name"],
                    DEFAULT_COMPANY["signature_path"],
                    now,
                    now,
                ),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM company WHERE owner_user_id = ?", (owner_user_id,)).fetchone()
    company = row_to_dict(row) or {}
    normalized = DEFAULT_COMPANY.copy()
    normalized.update({key: value for key, value in company.items() if value is not None})
    return normalized


def update_company(payload: dict[str, Any], owner_user_id: int | None = None) -> dict[str, Any]:
    """Update the singleton company settings record."""
    allowed_fields = [
        "name",
        "legal_name",
        "gstin",
        "pan",
        "address",
        "state",
        "phone",
        "email",
        "website",
        "bank_name",
        "bank_account_name",
        "bank_account_number",
        "bank_ifsc",
        "upi_id",
        "logo_path",
        "invoice_prefix",
        "current_number",
        "invoice_number_padding",
        "currency_symbol",
        "default_payment_terms",
        "terms_and_conditions",
        "authorized_signatory_name",
        "signature_path",
    ]
    current = get_company(owner_user_id)
    updates = {field: payload.get(field, current.get(field, "")) for field in allowed_fields}
    updates["name"] = str(updates["name"] or "").strip() or "Your Business Name"
    updates["invoice_prefix"] = str(updates["invoice_prefix"] or "INV").strip() or "INV"
    updates["current_number"] = int(updates.get("current_number") or 0)
    updates["invoice_number_padding"] = max(1, min(int(updates.get("invoice_number_padding") or 4), 10))
    updates["currency_symbol"] = str(updates.get("currency_symbol") or "Rs.").strip() or "Rs."

    with get_db_connection() as connection:
        connection.execute(
            """
            UPDATE company
            SET name = ?, legal_name = ?, gstin = ?, pan = ?, address = ?,
                state = ?, phone = ?, email = ?, website = ?, bank_name = ?,
                bank_account_name = ?, bank_account_number = ?, bank_ifsc = ?,
                upi_id = ?, logo_path = ?, invoice_prefix = ?, current_number = ?,
                invoice_number_padding = ?, currency_symbol = ?,
                default_payment_terms = ?, terms_and_conditions = ?,
                authorized_signatory_name = ?, signature_path = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updates["name"],
                updates["legal_name"],
                updates["gstin"],
                updates["pan"],
                updates["address"],
                updates["state"],
                updates["phone"],
                updates["email"],
                updates["website"],
                updates["bank_name"],
                updates["bank_account_name"],
                updates["bank_account_number"],
                updates["bank_ifsc"],
                updates["upi_id"],
                updates["logo_path"],
                updates["invoice_prefix"],
                updates["current_number"],
                updates["invoice_number_padding"],
                updates["currency_symbol"],
                updates["default_payment_terms"],
                updates["terms_and_conditions"],
                updates["authorized_signatory_name"],
                updates["signature_path"],
                now_iso(),
                current.get("id", 1),
            ),
        )
        connection.commit()
    return get_company(owner_user_id)

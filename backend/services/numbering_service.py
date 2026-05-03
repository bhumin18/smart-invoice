"""Invoice numbering service."""

from __future__ import annotations

import re

from models.company_model import get_company
from utils.helpers import get_db_connection


def _highest_existing_number(prefix: str, owner_user_id: int | None = None) -> int:
    """Return the highest existing numeric suffix for a prefix."""
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    highest = 0
    query = "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ?"
    params: tuple[object, ...] = (f"{prefix}-%",)
    if owner_user_id is not None:
        query += " AND owner_user_id = ?"
        params = (f"{prefix}-%", owner_user_id)
    with get_db_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    for row in rows:
        match = pattern.match(str(row["invoice_number"]))
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def get_next_invoice_number(owner_user_id: int | None = None) -> str:
    """Increment and return the next invoice number from the database."""
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT invoice_prefix, current_number, invoice_number_padding FROM company WHERE owner_user_id = ?",
            (owner_user_id,),
        ).fetchone() if owner_user_id is not None else connection.execute(
            "SELECT invoice_prefix, current_number, invoice_number_padding FROM company ORDER BY id LIMIT 1"
        ).fetchone()
        prefix = str(row["invoice_prefix"] if row else "INV").strip() or "INV"
        current_number = int(row["current_number"] if row else 0)
        padding = int(row["invoice_number_padding"] if row else 4)
        next_number = max(current_number, _highest_existing_number(prefix, owner_user_id)) + 1
        if owner_user_id is not None:
            connection.execute("UPDATE company SET current_number = ? WHERE owner_user_id = ?", (next_number, owner_user_id))
        else:
            connection.execute("UPDATE company SET current_number = ? WHERE id = 1", (next_number,))
        connection.commit()
    return f"{prefix}-{next_number:0{padding}d}"


def preview_next_invoice_number(owner_user_id: int | None = None) -> str:
    """Return the next invoice number without incrementing it."""
    company = get_company(owner_user_id)
    prefix = str(company.get("invoice_prefix", "INV")).strip() or "INV"
    padding = int(company.get("invoice_number_padding", 4) or 4)
    next_number = max(int(company.get("current_number", 0)), _highest_existing_number(prefix, owner_user_id)) + 1
    return f"{prefix}-{next_number:0{padding}d}"


def sync_invoice_number(invoice_number: str, owner_user_id: int | None = None) -> None:
    """Advance the stored sequence if a manually supplied invoice number is in series."""
    company = get_company(owner_user_id)
    prefix = str(company.get("invoice_prefix", "INV")).strip() or "INV"
    match = re.match(rf"^{re.escape(prefix)}-(\d+)$", invoice_number.strip())
    if not match:
        return
    used_number = int(match.group(1))
    current_number = int(company.get("current_number", 0))
    if used_number <= current_number:
        return
    with get_db_connection() as connection:
        if owner_user_id is not None:
            connection.execute("UPDATE company SET current_number = ? WHERE owner_user_id = ?", (used_number, owner_user_id))
        else:
            connection.execute("UPDATE company SET current_number = ? WHERE id = 1", (used_number,))
        connection.commit()

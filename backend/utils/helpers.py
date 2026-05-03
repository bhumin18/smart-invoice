"""Shared helpers for the Flask backend."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from flask import jsonify

from config import (
    ASSETS_OUTPUT_PATH,
    BACKUPS_OUTPUT_PATH,
    INVOICE_OUTPUT_PATH,
    LOG_LEVEL,
    MAX_GST_RATE,
    OUTPUT_BASE_DIR,
    REPORT_OUTPUT_PATH,
    SQLITE_DATABASE_PATH,
    validate_database_config,
)


BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = SQLITE_DATABASE_PATH
OUTPUT_DIR = OUTPUT_BASE_DIR
INVOICE_OUTPUT_DIR = INVOICE_OUTPUT_PATH
REPORT_OUTPUT_DIR = REPORT_OUTPUT_PATH
ASSETS_OUTPUT_DIR = ASSETS_OUTPUT_PATH
BACKUPS_OUTPUT_DIR = BACKUPS_OUTPUT_PATH

DATE_FORMAT = "%Y-%m-%d"


def setup_logging() -> None:
    """Configure application logging once at startup."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def ensure_directories() -> None:
    """Create required runtime folders if they are missing."""
    for folder in [DATABASE_DIR, INVOICE_OUTPUT_DIR, REPORT_OUTPUT_DIR, ASSETS_OUTPUT_DIR, BACKUPS_OUTPUT_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def get_db_connection() -> sqlite3.Connection:
    """Open a SQLite connection with row dictionaries enabled."""
    validate_database_config()
    ensure_directories()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def api_response(
    success: bool,
    data: Any = None,
    message: str = "",
    status_code: int = 200,
    errors: dict[str, Any] | None = None,
):
    """Return the standard API JSON envelope."""
    body = {"success": success, "data": data if data is not None else {}, "message": message}
    if errors is not None:
        body["errors"] = errors
    return jsonify(body), status_code


class ValidationError(Exception):
    """Structured validation error for request payloads."""

    def __init__(self, errors: dict[str, str], message: str = "Validation error") -> None:
        super().__init__(message)
        self.errors = errors
        self.message = message


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a SQLite row to a plain dictionary."""
    return dict(row) if row is not None else None


def parse_date(value: str | None, field_name: str = "date") -> str:
    """Validate and normalize a date string in YYYY-MM-DD format."""
    if not value:
        return date.today().isoformat()
    try:
        return datetime.strptime(value, DATE_FORMAT).date().isoformat()
    except ValueError as exc:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format") from exc


def now_iso() -> str:
    """Return the current timestamp in ISO format."""
    return datetime.now().isoformat(timespec="seconds")


def calculate_item_totals(item: dict[str, Any]) -> dict[str, Any]:
    """Calculate subtotal, GST, and total for one invoice item."""
    quantity = round(float(item.get("quantity", 0)), 2)
    price = round(float(item.get("price", 0)), 2)
    gst_rate = round(float(item.get("gst_rate", 0)), 2)
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero")
    if price < 0:
        raise ValueError("price cannot be negative")
    if gst_rate < 0 or gst_rate > MAX_GST_RATE:
        raise ValueError(f"gst_rate must be between 0 and {MAX_GST_RATE:g}")
    line_subtotal = round(quantity * price, 2)
    line_gst = round(line_subtotal * gst_rate / 100, 2)
    line_total = round(line_subtotal + line_gst, 2)
    if line_subtotal < 0 or line_gst < 0 or line_total < 0:
        raise ValueError("calculated totals cannot be negative")
    return {
        "item_name": str(item.get("item_name") or item.get("name") or "").strip(),
        "description": str(item.get("description", "")).strip(),
        "hsn_sac": str(item.get("hsn_sac", "")).strip(),
        "quantity": quantity,
        "price": price,
        "gst_rate": gst_rate,
        "line_subtotal": line_subtotal,
        "line_gst": line_gst,
        "line_total": line_total,
    }


def calculate_invoice_totals(items: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate subtotal, total GST, and grand total for invoice items."""
    if not items:
        raise ValueError("invoice must contain at least one item")
    subtotal = round(sum(float(item["line_subtotal"]) for item in items), 2)
    gst_amount = round(sum(float(item["line_gst"]) for item in items), 2)
    total = round(subtotal + gst_amount, 2)
    if subtotal < 0 or gst_amount < 0 or total < 0:
        raise ValueError("invoice totals cannot be negative")
    return {"subtotal": subtotal, "gst_amount": gst_amount, "total": total}


def get_gst_breakdown(
    items: list[dict[str, Any]], supply_type: str = "intrastate"
) -> list[dict[str, float]]:
    """Group tax by GST rate and split CGST/SGST or IGST."""
    grouped: dict[float, dict[str, float]] = {}
    for item in items:
        rate = float(item["gst_rate"])
        grouped.setdefault(rate, {"gst_rate": rate, "taxable_amount": 0.0, "gst_amount": 0.0})
        grouped[rate]["taxable_amount"] += float(item["line_subtotal"])
        grouped[rate]["gst_amount"] += float(item["line_gst"])

    is_interstate = supply_type.lower() == "interstate"
    rows: list[dict[str, float]] = []
    for rate, values in sorted(grouped.items()):
        gst_amount = round(values["gst_amount"], 2)
        if is_interstate:
            cgst = 0.0
            sgst = 0.0
            igst = gst_amount
        else:
            cgst = round(gst_amount / 2, 2)
            sgst = round(gst_amount - cgst, 2)
            igst = 0.0
        rows.append(
            {
                "gst_rate": rate,
                "taxable_amount": round(values["taxable_amount"], 2),
                "gst_amount": gst_amount,
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
            }
        )
    return rows


def format_currency(value: float, symbol: str = "Rs.") -> str:
    """Format an amount for PDF display."""
    return f"{symbol} {float(value):,.2f}"

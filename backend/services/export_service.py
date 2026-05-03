"""Full data export service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from flask import send_file

from utils.helpers import REPORT_OUTPUT_DIR, ensure_directories, get_db_connection, now_iso


EXPORT_TABLES = {
    "company": "SELECT * FROM company",
    "invoices": "SELECT * FROM invoices ORDER BY id",
    "invoice_items": "SELECT * FROM invoice_items ORDER BY invoice_id, id",
    "invoice_payments": "SELECT * FROM invoice_payments ORDER BY invoice_id, id",
    "clients": "SELECT * FROM clients ORDER BY id",
    "products": "SELECT * FROM products ORDER BY id",
}


def _load_export_data() -> dict[str, list[dict[str, Any]]]:
    """Load exportable tables into plain dictionaries."""
    with get_db_connection() as connection:
        data: dict[str, list[dict[str, Any]]] = {}
        for name, query in EXPORT_TABLES.items():
            rows = connection.execute(query).fetchall()
            data[name] = [dict(row) for row in rows]
    return data


def export_json() -> str:
    """Write a full JSON export and return its path."""
    ensure_directories()
    stamp = now_iso().replace(":", "-")
    output_path = REPORT_OUTPUT_DIR / f"smart_invoice_export_{stamp}.json"
    payload = {"exported_at": now_iso(), "data": _load_export_data()}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(output_path)


def export_excel() -> str:
    """Write a full Excel export and return its path."""
    ensure_directories()
    stamp = now_iso().replace(":", "-")
    output_path = REPORT_OUTPUT_DIR / f"smart_invoice_export_{stamp}.xlsx"
    data = _load_export_data()
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, rows in data.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name[:31], index=False)
            worksheet = writer.sheets[sheet_name[:31]]
            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 45)
    return str(output_path)


def download_data_export(export_format: str):
    """Return a JSON or Excel full data export."""
    if export_format == "json":
        path = export_json()
    else:
        path = export_excel()
    return send_file(path, as_attachment=True, download_name=Path(path).name)

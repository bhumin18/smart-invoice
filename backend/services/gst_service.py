"""GST Excel report generation service."""

from __future__ import annotations

from typing import Any

import pandas as pd
from flask import send_file

from models.invoice_model import get_invoice_rows_for_period
from utils.helpers import REPORT_OUTPUT_DIR, ensure_directories, get_gst_breakdown


REPORT_COLUMNS = [
    "Invoice ID",
    "Invoice Number",
    "Date",
    "Client",
    "Client GSTIN",
    "Item",
    "GST %",
    "Taxable Amount",
    "CGST",
    "SGST",
    "IGST",
    "GST Amount",
    "Total",
]


def build_gst_dataframe(month: int, year: int, filters: dict[str, Any] | None = None) -> pd.DataFrame:
    """Build GST report data for a month and year."""
    rows: list[dict[str, Any]] = []
    for row in get_invoice_rows_for_period(month, year, filters):
        breakdown = get_gst_breakdown(
            [
                {
                    "gst_rate": row["gst_rate"],
                    "line_subtotal": row["line_subtotal"],
                    "line_gst": row["line_gst"],
                }
            ],
            row.get("supply_type", "intrastate"),
        )[0]
        rows.append(
            {
                "Invoice ID": row["id"],
                "Invoice Number": row["invoice_number"],
                "Date": row["date"],
                "Client": row["client_name"],
                "Client GSTIN": row["client_gstin"],
                "Item": row["item_name"],
                "GST %": row["gst_rate"],
                "Taxable Amount": row["line_subtotal"],
                "CGST": breakdown["cgst"],
                "SGST": breakdown["sgst"],
                "IGST": breakdown["igst"],
                "GST Amount": row["line_gst"],
                "Total": row["line_total"],
            }
        )
    return pd.DataFrame(rows, columns=REPORT_COLUMNS)


def generate_gst_report(month: int, year: int, filters: dict[str, Any] | None = None) -> tuple[str | None, pd.DataFrame]:
    """Generate an Excel GST report and return its path and DataFrame."""
    ensure_directories()
    df = build_gst_dataframe(month, year, filters)
    if df.empty:
        return None, df
    output_path = REPORT_OUTPUT_DIR / f"gst_report_{year}_{month:02d}.xlsx"
    summary_df = pd.DataFrame(
        [
            {"Metric": "total_sales", "Amount": round(float(df["Taxable Amount"].sum()), 2)},
            {"Metric": "total_gst", "Amount": round(float(df["GST Amount"].sum()), 2)},
            {"Metric": "total_cgst", "Amount": round(float(df["CGST"].sum()), 2)},
            {"Metric": "total_sgst", "Amount": round(float(df["SGST"].sum()), 2)},
            {"Metric": "total_igst", "Amount": round(float(df["IGST"].sum()), 2)},
            {"Metric": "grand_total", "Amount": round(float(df["Total"].sum()), 2)},
        ]
    )
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="GST Report")
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        worksheet = writer.sheets["GST Report"]
        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2
        summary_sheet = writer.sheets["Summary"]
        for column_cells in summary_sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            summary_sheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2
    return str(output_path), df


def download_gst_report(month: int, year: int, filters: dict[str, Any] | None = None):
    """Return a generated GST report as a Flask download response."""
    path, df = generate_gst_report(month, year, filters)
    if path is None or df.empty:
        return None
    return send_file(path, as_attachment=True, download_name=f"gst_report_{year}_{month:02d}.xlsx")

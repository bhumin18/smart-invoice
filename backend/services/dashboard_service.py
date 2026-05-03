"""Dashboard reporting service."""

from __future__ import annotations

from typing import Any

from models.invoice_model import get_invoice_summary, get_invoices
from utils.auth_context import user_scope


def get_dashboard_summary(current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return dashboard totals and recent invoices."""
    scope = user_scope(current_user)
    summary = get_invoice_summary(scope)
    recent = get_invoices(scope)[:5]
    return {
        "invoice_count": int(summary.get("invoice_count", 0) or 0),
        "void_count": int(summary.get("void_count", 0) or 0),
        "total_sales": round(float(summary.get("total_sales", 0) or 0), 2),
        "total_gst": round(float(summary.get("total_gst", 0) or 0), 2),
        "balance_due": round(float(summary.get("balance_due", 0) or 0), 2),
        "paid_sales": round(float(summary.get("paid_sales", 0) or 0), 2),
        "recent_invoices": recent,
    }

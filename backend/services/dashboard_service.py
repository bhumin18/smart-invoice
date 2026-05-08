"""Dashboard reporting service."""

from __future__ import annotations

from typing import Any

from models.invoice_model import get_dashboard_analytics as get_invoice_dashboard_analytics
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


def get_dashboard_analytics(current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return dashboard chart data."""
    analytics = get_invoice_dashboard_analytics(user_scope(current_user))
    return {
        "monthly": [
            {
                "month": row.get("month"),
                "revenue": round(float(row.get("revenue", 0) or 0), 2),
                "gst": round(float(row.get("gst", 0) or 0), 2),
            }
            for row in analytics.get("monthly", [])
        ],
        "status": [
            {
                "status": row.get("status") or "unknown",
                "count": int(row.get("count", 0) or 0),
                "amount": round(float(row.get("amount", 0) or 0), 2),
            }
            for row in analytics.get("status", [])
        ],
        "top_clients": [
            {
                "client_name": row.get("client_name") or "Unknown",
                "amount": round(float(row.get("amount", 0) or 0), 2),
                "invoice_count": int(row.get("invoice_count", 0) or 0),
            }
            for row in analytics.get("top_clients", [])
        ],
        "overdue": analytics.get("overdue", []),
    }

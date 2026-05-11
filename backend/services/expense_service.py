"""Business logic for expense tracking."""

from __future__ import annotations

from typing import Any

from config import MAX_GST_RATE
from models.expense_model import (
    delete_expense_record,
    get_expense_by_id,
    insert_expense,
    list_expenses,
    update_expense_record,
)
from utils.auth_context import user_scope
from utils.helpers import ValidationError, parse_date


def _normalize_payload(payload: dict[str, Any], current_user: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate and normalize an expense payload."""
    merged = {**(existing or {}), **payload}
    errors: dict[str, str] = {}
    if not str(merged.get("vendor_name", "")).strip():
        errors["vendor_name"] = "vendor_name is required"
    try:
        taxable_amount = round(float(merged.get("taxable_amount", 0)), 2)
        gst_rate = round(float(merged.get("gst_rate", 0)), 2)
    except (TypeError, ValueError):
        raise ValidationError({"expense": "taxable_amount and gst_rate must be valid numbers"})
    if taxable_amount < 0:
        errors["taxable_amount"] = "taxable_amount must be greater than or equal to zero"
    if gst_rate < 0 or gst_rate > MAX_GST_RATE:
        errors["gst_rate"] = f"gst_rate must be between 0 and {MAX_GST_RATE:g}"
    if errors:
        raise ValidationError(errors)

    gst_amount = round(taxable_amount * gst_rate / 100, 2)
    return {
        "owner_user_id": (existing or {}).get("owner_user_id") or current_user.get("id"),
        "vendor_name": str(merged.get("vendor_name", "")).strip(),
        "gstin": str(merged.get("gstin", "")).strip().upper(),
        "category": str(merged.get("category", "")).strip(),
        "expense_date": parse_date(merged.get("expense_date") or merged.get("date"), "expense_date"),
        "taxable_amount": taxable_amount,
        "gst_rate": gst_rate,
        "gst_amount": gst_amount,
        "total": round(taxable_amount + gst_amount, 2),
        "payment_mode": str(merged.get("payment_mode", "")).strip(),
        "notes": str(merged.get("notes", "")).strip(),
    }


def get_expenses(current_user: dict[str, Any]) -> list[dict[str, Any]]:
    """List expenses for the current user."""
    return list_expenses(**user_scope(current_user))


def get_expense(expense_id: int, current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Return one expense."""
    return get_expense_by_id(expense_id, **user_scope(current_user))


def create_expense(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    """Create an expense."""
    return insert_expense(_normalize_payload(payload, current_user))


def update_expense(expense_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Update an expense."""
    existing = get_expense_by_id(expense_id, **user_scope(current_user))
    if existing is None:
        return None
    return update_expense_record(expense_id, _normalize_payload(payload, current_user, existing))


def delete_expense(expense_id: int, current_user: dict[str, Any]) -> bool:
    """Delete an expense."""
    return delete_expense_record(expense_id, **user_scope(current_user))


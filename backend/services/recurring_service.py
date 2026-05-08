"""Recurring invoice service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from models.recurring_model import (
    delete_recurring_record,
    due_recurring_profiles,
    insert_recurring,
    list_recurring,
    update_recurring_record,
)
from services.invoice_service import create_invoice
from utils.auth_context import user_scope
from utils.helpers import ValidationError, parse_date


VALID_FREQUENCIES = {"monthly", "quarterly", "yearly"}


def _add_frequency(value: str, frequency: str) -> str:
    """Advance a date by recurring frequency."""
    current = datetime.strptime(value, "%Y-%m-%d").date()
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
    year = current.year + (current.month - 1 + months) // 12
    month = (current.month - 1 + months) % 12 + 1
    day = min(current.day, 28)
    return date(year, month, day).isoformat()


def create_recurring_profile(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    """Create a recurring invoice profile."""
    invoice_payload = payload.get("invoice") or payload.get("payload") or {}
    name = str(payload.get("name") or invoice_payload.get("client_name") or "Recurring Invoice").strip()
    client_name = str(invoice_payload.get("client_name") or "").strip()
    frequency = str(payload.get("frequency", "monthly")).lower()
    if frequency not in VALID_FREQUENCIES:
        raise ValidationError({"frequency": "frequency must be monthly, quarterly, or yearly"})
    if not client_name:
        raise ValidationError({"client_name": "Recurring invoice must include client_name"})
    next_run_date = parse_date(str(payload.get("next_run_date") or invoice_payload.get("date") or ""), "next_run_date")
    invoice_payload.pop("invoice_number", None)
    return insert_recurring(
        {
            "owner_user_id": current_user.get("id"),
            "name": name,
            "client_name": client_name,
            "payload": invoice_payload,
            "frequency": frequency,
            "next_run_date": next_run_date,
            "active": bool(payload.get("active", True)),
        }
    )


def get_recurring_profiles(current_user: dict[str, Any]) -> list[dict[str, Any]]:
    """List recurring profiles."""
    return list_recurring(**user_scope(current_user))


def update_recurring_profile(recurring_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Update recurring profile."""
    scope = user_scope(current_user)
    profiles = [profile for profile in list_recurring(**scope) if int(profile["id"]) == recurring_id]
    if not profiles:
        return None
    existing = profiles[0]
    merged = {**existing, **payload}
    if "invoice" in payload:
        merged["payload"] = payload["invoice"]
    if str(merged.get("frequency", "monthly")) not in VALID_FREQUENCIES:
        raise ValidationError({"frequency": "frequency must be monthly, quarterly, or yearly"})
    return update_recurring_record(recurring_id, merged)


def delete_recurring_profile(recurring_id: int, current_user: dict[str, Any]) -> bool:
    """Delete recurring profile."""
    return delete_recurring_record(recurring_id, **user_scope(current_user))


def run_due_recurring(current_user: dict[str, Any]) -> dict[str, Any]:
    """Generate due recurring invoices."""
    today = date.today().isoformat()
    generated = []
    for profile in due_recurring_profiles(today, **user_scope(current_user)):
        payload = dict(profile.get("payload") or {})
        payload["date"] = today
        invoice = create_invoice(payload, current_user)
        next_run_date = _add_frequency(str(profile["next_run_date"]), str(profile["frequency"]))
        update_recurring_record(
            int(profile["id"]),
            {**profile, "next_run_date": next_run_date, "last_generated_invoice_id": invoice.get("id")},
        )
        generated.append(invoice)
    return {"generated_count": len(generated), "generated": generated}

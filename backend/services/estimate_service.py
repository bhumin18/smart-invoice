"""Business logic for quotations and estimates."""

from __future__ import annotations

from typing import Any

from models.estimate_model import (
    delete_estimate_record,
    estimate_number_exists,
    get_estimate_by_id,
    insert_estimate,
    list_estimates,
    mark_estimate_converted,
    next_estimate_number,
    update_estimate_record,
)
from services.invoice_service import create_invoice
from utils.auth_context import user_scope
from utils.helpers import ValidationError, calculate_invoice_totals, calculate_item_totals, parse_date


VALID_STATUSES = {"draft", "sent", "accepted", "rejected", "expired", "converted"}


def _normalize_payload(
    payload: dict[str, Any],
    current_user: dict[str, Any],
    estimate_id: int | None = None,
    current_estimate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate and normalize an estimate payload."""
    errors: dict[str, str] = {}
    if not str(payload.get("client_name", "")).strip():
        errors["client_name"] = "client_name is required"
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        errors["items"] = "items must contain at least one item"
    if errors:
        raise ValidationError(errors)

    try:
        calculated_items = [calculate_item_totals(item) for item in items]
        totals = calculate_invoice_totals(calculated_items)
        estimate_date = parse_date(payload.get("date"), "date")
        valid_until = parse_date(payload.get("valid_until"), "valid_until") if payload.get("valid_until") else ""
    except ValueError as exc:
        raise ValidationError({"estimate": str(exc)}) from exc

    owner_user_id = int((current_estimate or {}).get("owner_user_id") or current_user.get("id") or 0) or None
    estimate_number = str(payload.get("estimate_number") or (current_estimate or {}).get("estimate_number") or next_estimate_number(owner_user_id)).strip()
    if estimate_number_exists(estimate_number, owner_user_id=owner_user_id, exclude_estimate_id=estimate_id):
        raise ValidationError({"estimate_number": "estimate_number already exists"})

    status = str(payload.get("status") or (current_estimate or {}).get("status") or "draft").strip().lower()
    if status not in VALID_STATUSES:
        raise ValidationError({"status": "status is invalid"})

    return (
        {
            "owner_user_id": owner_user_id,
            "estimate_number": estimate_number,
            "client_name": str(payload["client_name"]).strip(),
            "client_gstin": str(payload.get("client_gstin", "")).strip(),
            "client_address": str(payload.get("client_address", "")).strip(),
            "date": estimate_date,
            "valid_until": valid_until,
            "supply_type": str(payload.get("supply_type", "intrastate")).strip().lower() or "intrastate",
            "place_of_supply": str(payload.get("place_of_supply", "")).strip(),
            "subtotal": totals["subtotal"],
            "gst_amount": totals["gst_amount"],
            "total": totals["total"],
            "status": status,
            "notes": str(payload.get("notes", "")).strip(),
            "converted_invoice_id": (current_estimate or {}).get("converted_invoice_id"),
        },
        calculated_items,
    )


def get_estimates(current_user: dict[str, Any]) -> list[dict[str, Any]]:
    """List estimates for the current user."""
    return list_estimates(**user_scope(current_user))


def get_estimate(estimate_id: int, current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Return one estimate."""
    return get_estimate_by_id(estimate_id, **user_scope(current_user))


def create_estimate(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    """Create an estimate."""
    estimate, items = _normalize_payload(payload, current_user)
    return insert_estimate(estimate, items)


def update_estimate(estimate_id: int, payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Update an estimate."""
    current = get_estimate_by_id(estimate_id, **user_scope(current_user))
    if current is None:
        return None
    estimate, items = _normalize_payload({**current, **payload}, current_user, estimate_id, current)
    return update_estimate_record(estimate_id, estimate, items)


def delete_estimate(estimate_id: int, current_user: dict[str, Any]) -> bool:
    """Delete an estimate."""
    return delete_estimate_record(estimate_id, **user_scope(current_user))


def convert_estimate_to_invoice(estimate_id: int, current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Convert an accepted estimate into a new invoice."""
    estimate = get_estimate_by_id(estimate_id, **user_scope(current_user))
    if estimate is None:
        return None
    if estimate.get("converted_invoice_id"):
        raise ValidationError({"estimate": "Estimate is already converted"})
    invoice = create_invoice(
        {
            "client_name": estimate["client_name"],
            "client_gstin": estimate.get("client_gstin", ""),
            "client_address": estimate.get("client_address", ""),
            "date": estimate.get("date"),
            "supply_type": estimate.get("supply_type", "intrastate"),
            "place_of_supply": estimate.get("place_of_supply", ""),
            "status": "sent",
            "notes": f"Converted from estimate {estimate.get('estimate_number')}",
            "items": estimate.get("items", []),
        },
        current_user,
    )
    mark_estimate_converted(estimate_id, int(invoice["id"]))
    return invoice


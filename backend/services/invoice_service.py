"""Business logic for invoices."""

from __future__ import annotations

import logging
from typing import Any

from config import DEFAULT_SUPPLY_TYPE, MAX_GST_RATE
from models.invoice_model import (
    delete_invoice,
    get_invoice_by_id,
    get_invoice_payments,
    get_invoices,
    insert_invoice,
    insert_invoice_payment,
    invoice_number_exists,
    replace_invoice,
)
from services.numbering_service import get_next_invoice_number, sync_invoice_number
from services.auth_service import require_permission
from utils.auth_context import is_admin, user_scope
from utils.helpers import ValidationError, calculate_invoice_totals, calculate_item_totals, now_iso, parse_date


VALID_SUPPLY_TYPES = {"intrastate", "interstate"}
logger = logging.getLogger(__name__)


def validate_invoice_payload(payload: dict[str, Any]) -> dict[str, str]:
    """Validate the invoice creation payload."""
    errors: dict[str, str] = {}
    if not str(payload.get("client_name", "")).strip():
        errors["client_name"] = "client_name is required"
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        errors["items"] = "items must contain at least one item"
        return errors

    for index, item in enumerate(items):
        prefix = f"items[{index}]"
        if not str(item.get("item_name") or item.get("name") or "").strip():
            errors[f"{prefix}.item_name"] = "item_name is required"
        try:
            if float(item.get("quantity", 0)) <= 0:
                errors[f"{prefix}.quantity"] = "quantity must be greater than zero"
            if float(item.get("price", 0)) < 0:
                errors[f"{prefix}.price"] = "price must be greater than or equal to zero"
            gst_rate = float(item.get("gst_rate", 0))
            if gst_rate < 0 or gst_rate > MAX_GST_RATE:
                errors[f"{prefix}.gst_rate"] = f"gst_rate must be between 0 and {MAX_GST_RATE:g}"
        except (TypeError, ValueError):
            errors[prefix] = "item contains invalid numeric values"

    supply_type = str(payload.get("supply_type", DEFAULT_SUPPLY_TYPE)).lower()
    if supply_type not in VALID_SUPPLY_TYPES:
        errors["supply_type"] = "supply_type must be intrastate or interstate"
    return errors


def build_invoice_payload(
    payload: dict[str, Any],
    invoice_number: str | None = None,
    exclude_invoice_id: int | None = None,
    current_invoice: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate input and build normalized invoice and item dictionaries."""
    errors = validate_invoice_payload(payload)
    if errors:
        raise ValidationError(errors)

    try:
        date_value = parse_date(payload.get("date"), "date")
        due_date = parse_date(payload.get("due_date"), "due_date") if payload.get("due_date") else ""
    except ValueError as exc:
        field = "due_date" if "due_date" in str(exc) else "date"
        raise ValidationError({field: str(exc)}) from exc
    supply_type = str(payload.get("supply_type", DEFAULT_SUPPLY_TYPE)).lower()
    try:
        calculated_items = [calculate_item_totals(item) for item in payload["items"]]
        totals = calculate_invoice_totals(calculated_items)
    except ValueError as exc:
        raise ValidationError({"items": str(exc)}) from exc
    requested_number = str(payload.get("invoice_number") or "").strip()
    owner_user_id = payload.get("owner_user_id")
    final_invoice_number = invoice_number or requested_number or get_next_invoice_number(
        int(owner_user_id) if owner_user_id else None
    )
    if invoice_number_exists(
        final_invoice_number,
        exclude_invoice_id=exclude_invoice_id,
        owner_user_id=int(owner_user_id) if owner_user_id else None,
        include_all=False,
    ):
        raise ValidationError({"invoice_number": "invoice_number already exists"})

    invoice = {
        "invoice_number": final_invoice_number,
        "owner_user_id": owner_user_id,
        "client_name": str(payload["client_name"]).strip(),
        "client_gstin": str(payload.get("client_gstin", "")).strip(),
        "client_address": str(payload.get("client_address", "")).strip(),
        "date": date_value,
        "due_date": due_date,
        "supply_type": supply_type,
        "place_of_supply": str(payload.get("place_of_supply", "")).strip(),
        "subtotal": totals["subtotal"],
        "gst_amount": totals["gst_amount"],
        "total": totals["total"],
        "status": str(payload.get("status", "sent")).strip().lower() or "sent",
        "payment_terms": str(payload.get("payment_terms", "")).strip(),
        "amount_paid": float(current_invoice.get("amount_paid", 0)) if current_invoice else 0.0,
        "balance_due": totals["total"],
        "notes": str(payload.get("notes", "")).strip(),
        "void_reason": str(current_invoice.get("void_reason", "")) if current_invoice else "",
        "voided_at": str(current_invoice.get("voided_at", "")) if current_invoice else "",
    }
    invoice["balance_due"] = round(max(invoice["total"] - invoice["amount_paid"], 0), 2)
    if invoice["amount_paid"] > 0:
        invoice["status"] = "paid" if invoice["balance_due"] <= 0 else "partially paid"
    return invoice, calculated_items


def create_invoice(payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create an invoice, calculate totals, and persist it."""
    current_user = current_user or {}
    require_permission(current_user, "can_create_invoices")
    payload = {**payload, "owner_user_id": current_user.get("id")}
    invoice, calculated_items = build_invoice_payload(payload)
    saved = insert_invoice(invoice, calculated_items)
    sync_invoice_number(str(saved.get("invoice_number", "")), current_user.get("id"))
    logger.info("Created invoice %s", saved.get("invoice_number"))
    return saved


def update_invoice(invoice_id: int, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Update an existing invoice and recalculate totals."""
    scope = user_scope(current_user)
    current = get_invoice_by_id(invoice_id, **scope)
    if current is None:
        return None
    invoice, calculated_items = build_invoice_payload(
        payload,
        invoice_number=str(payload.get("invoice_number") or current["invoice_number"]),
        exclude_invoice_id=invoice_id,
        current_invoice=current,
    )
    invoice["owner_user_id"] = current.get("owner_user_id")
    updated = replace_invoice(invoice_id, invoice, calculated_items)
    if updated:
        logger.info("Updated invoice %s", updated.get("invoice_number"))
    return updated


def clone_invoice(invoice_id: int, current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Duplicate an invoice into a new draft with a fresh invoice number."""
    current = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if current is None:
        return None
    clone_payload = {
        "invoice_number": get_next_invoice_number((current_user or {}).get("id")),
        "client_name": current.get("client_name", ""),
        "client_gstin": current.get("client_gstin", ""),
        "client_address": current.get("client_address", ""),
        "date": current.get("date", ""),
        "due_date": current.get("due_date", ""),
        "supply_type": current.get("supply_type", DEFAULT_SUPPLY_TYPE),
        "place_of_supply": current.get("place_of_supply", ""),
        "status": "draft",
        "payment_terms": current.get("payment_terms", ""),
        "notes": current.get("notes", ""),
        "items": current.get("items", []),
    }
    cloned = create_invoice(clone_payload, current_user)
    logger.info("Cloned invoice %s to %s", current.get("invoice_number"), cloned.get("invoice_number"))
    return cloned


def void_invoice(invoice_id: int, reason: str = "", current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Void an invoice while keeping the record."""
    current = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if current is None:
        return None
    if str(current.get("status", "")).lower() == "void":
        return current
    invoice = {
        **current,
        "status": "void",
        "void_reason": reason.strip(),
        "voided_at": now_iso(),
        "balance_due": 0.0,
    }
    updated = replace_invoice(invoice_id, invoice, current.get("items", []))
    if updated:
        logger.info("Voided invoice %s", updated.get("invoice_number"))
    return updated


def record_payment(
    invoice_id: int,
    amount: float,
    payment_date: str,
    mode: str,
    reference: str = "",
    notes: str = "",
    current_user: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Record an offline payment against an invoice."""
    invoice = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if invoice is None:
        return None
    if str(invoice.get("status", "")).lower() == "void":
        raise ValidationError({"payment": "Cannot record payment for a void invoice"})
    if amount <= 0:
        raise ValidationError({"amount": "Payment amount must be greater than zero"})
    payment_date = parse_date(payment_date, "payment_date")
    insert_invoice_payment(invoice_id, payment_date, round(float(amount), 2), mode.strip() or "Bank Transfer", reference.strip(), notes.strip())
    payments = get_invoice_payments(invoice_id)
    amount_paid = round(sum(float(payment.get("amount", 0)) for payment in payments), 2)
    total = float(invoice.get("total", 0))
    balance_due = round(max(total - amount_paid, 0), 2)
    status = "paid" if balance_due <= 0 else "partially paid"
    updated = replace_invoice(
        invoice_id,
        {
            **invoice,
            "amount_paid": amount_paid,
            "balance_due": balance_due,
            "status": status,
        },
        invoice.get("items", []),
    )
    if updated:
        logger.info("Recorded payment for invoice %s", updated.get("invoice_number"))
    return updated


def remove_invoice(invoice_id: int, current_user: dict[str, Any] | None = None) -> bool:
    """Delete an invoice."""
    scope = user_scope(current_user)
    deleted = delete_invoice(invoice_id, **scope)
    if deleted:
        logger.info("Deleted invoice id=%s", invoice_id)
    return deleted


def list_invoices(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return all invoices."""
    return get_invoices(filters)


def get_invoice(invoice_id: int, current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return a single invoice by ID."""
    return get_invoice_by_id(invoice_id, **user_scope(current_user))

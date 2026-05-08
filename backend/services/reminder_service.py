"""Payment reminder service."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from models.invoice_model import get_invoices
from models.client_model import list_clients
from services.email_service import send_invoice_email
from utils.auth_context import user_scope
from utils.helpers import ValidationError


def get_payment_reminders(days_ahead: int, current_user: dict[str, Any]) -> dict[str, Any]:
    """Return invoices that should receive reminders."""
    today = date.today()
    ahead = today + timedelta(days=max(0, int(days_ahead)))
    invoices = get_invoices(user_scope(current_user))
    due = []
    overdue = []
    for invoice in invoices:
        if str(invoice.get("status", "")).lower() in {"paid", "void"}:
            continue
        if float(invoice.get("balance_due", invoice.get("total", 0)) or 0) <= 0:
            continue
        due_date = str(invoice.get("due_date") or "")
        if not due_date:
            continue
        parsed = date.fromisoformat(due_date)
        if parsed < today:
            overdue.append(invoice)
        elif parsed <= ahead:
            due.append(invoice)
    return {"due_soon": due, "overdue": overdue}


def send_payment_reminders(days_ahead: int, current_user: dict[str, Any]) -> dict[str, Any]:
    """Email reminder messages for due and overdue invoices."""
    reminders = get_payment_reminders(days_ahead, current_user)
    clients = list_clients(**user_scope(current_user))
    email_by_name = {str(client.get("name", "")).strip().lower(): str(client.get("email", "")).strip() for client in clients}
    sent = []
    errors = []
    for invoice in reminders["overdue"] + reminders["due_soon"]:
        to_email = email_by_name.get(str(invoice.get("client_name", "")).strip().lower(), "")
        if not to_email:
            errors.append({"invoice_number": invoice.get("invoice_number"), "message": "Client email is missing"})
            continue
        try:
            sent.append(
                send_invoice_email(
                    invoice,
                    {
                        "to_email": to_email,
                        "subject": f"Payment reminder for invoice {invoice.get('invoice_number')}",
                        "message": (
                            f"Dear {invoice.get('client_name')},\n\n"
                            f"This is a reminder for invoice {invoice.get('invoice_number')} "
                            f"with balance due {invoice.get('balance_due')}.\n\nThank you."
                        ),
                    },
                )
            )
        except ValidationError as exc:
            errors.append({"invoice_number": invoice.get("invoice_number"), "message": exc.message, "errors": exc.errors})
    return {"sent_count": len(sent), "error_count": len(errors), "errors": errors[:25]}

"""Payment reminder service."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from models.invoice_model import get_invoices
from models.client_model import list_clients
from models.reminder_model import insert_reminder_log, list_reminder_logs
from models.settings_model import get_setting, set_setting
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
            insert_reminder_log(
                {
                    "owner_user_id": invoice.get("owner_user_id"),
                    "invoice_id": invoice.get("id"),
                    "invoice_number": invoice.get("invoice_number"),
                    "recipient_email": "",
                    "status": "skipped",
                    "message": "Client email is missing",
                }
            )
            errors.append({"invoice_number": invoice.get("invoice_number"), "message": "Client email is missing"})
            continue
        template = get_setting(
            "reminder.email_template",
            "Dear {client_name},\n\nThis is a reminder for invoice {invoice_number} with balance due {balance_due}.\n\nThank you.",
        )
        message = template.format(
            client_name=invoice.get("client_name"),
            invoice_number=invoice.get("invoice_number"),
            balance_due=invoice.get("balance_due"),
            due_date=invoice.get("due_date"),
        )
        try:
            sent.append(
                send_invoice_email(
                    invoice,
                    {
                        "to_email": to_email,
                        "subject": f"Payment reminder for invoice {invoice.get('invoice_number')}",
                        "message": message,
                    },
                )
            )
            insert_reminder_log(
                {
                    "owner_user_id": invoice.get("owner_user_id"),
                    "invoice_id": invoice.get("id"),
                    "invoice_number": invoice.get("invoice_number"),
                    "recipient_email": to_email,
                    "status": "sent",
                    "message": "Reminder sent",
                }
            )
        except ValidationError as exc:
            insert_reminder_log(
                {
                    "owner_user_id": invoice.get("owner_user_id"),
                    "invoice_id": invoice.get("id"),
                    "invoice_number": invoice.get("invoice_number"),
                    "recipient_email": to_email,
                    "status": "failed",
                    "message": exc.message,
                }
            )
            errors.append({"invoice_number": invoice.get("invoice_number"), "message": exc.message, "errors": exc.errors})
    return {"sent_count": len(sent), "error_count": len(errors), "errors": errors[:25]}


def get_reminder_settings(current_user: dict[str, Any]) -> dict[str, Any]:
    """Return reminder settings and history."""
    scope = user_scope(current_user)
    return {
        "auto_enabled": get_setting("reminder.auto_enabled", "false").lower() == "true",
        "days_ahead": int(get_setting("reminder.days_ahead", "7") or 7),
        "email_template": get_setting(
            "reminder.email_template",
            "Dear {client_name},\n\nThis is a reminder for invoice {invoice_number} with balance due {balance_due}.\n\nThank you.",
        ),
        "history": list_reminder_logs(**scope, limit=50),
    }


def update_reminder_settings(payload: dict[str, Any], current_user: dict[str, Any]) -> dict[str, Any]:
    """Update reminder settings."""
    if "auto_enabled" in payload:
        set_setting("reminder.auto_enabled", "true" if bool(payload["auto_enabled"]) else "false")
    if "days_ahead" in payload:
        set_setting("reminder.days_ahead", str(max(0, int(payload["days_ahead"]))))
    if "email_template" in payload:
        set_setting("reminder.email_template", str(payload["email_template"]))
    return get_reminder_settings(current_user)


def run_auto_reminders(current_user: dict[str, Any]) -> dict[str, Any]:
    """Run auto reminder job if enabled."""
    settings = get_reminder_settings(current_user)
    if not settings["auto_enabled"]:
        return {"sent_count": 0, "skipped": True, "message": "Auto reminders are disabled"}
    return send_payment_reminders(settings["days_ahead"], current_user)

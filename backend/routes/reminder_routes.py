"""Payment reminder API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.reminder_service import (
    get_payment_reminders,
    get_reminder_settings,
    run_auto_reminders,
    send_payment_reminders,
    update_reminder_settings,
)
from utils.helpers import ValidationError, api_response


reminder_bp = Blueprint("reminder_routes", __name__, url_prefix="/api/reminders")
logger = logging.getLogger(__name__)


@reminder_bp.get("/payments")
def payment_reminders_route():
    """Preview invoices due soon and overdue."""
    try:
        days = int(request.args.get("days", "7"))
        return api_response(True, get_payment_reminders(days, getattr(g, "current_user", {}) or {}), "Payment reminders fetched successfully")
    except ValueError:
        return api_response(False, {}, "days must be a valid number", 400)
    except Exception as exc:
        logger.exception("Payment reminder preview failed")
        return api_response(False, {}, "Failed to fetch payment reminders", 500, {"error": str(exc)})


@reminder_bp.post("/payments/send")
def send_payment_reminders_route():
    """Send payment reminder emails for due invoices."""
    try:
        days = int((request.get_json(silent=True) or {}).get("days", 7))
        return api_response(True, send_payment_reminders(days, getattr(g, "current_user", {}) or {}), "Payment reminders processed successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except ValueError:
        return api_response(False, {}, "days must be a valid number", 400)
    except Exception as exc:
        logger.exception("Payment reminder send failed")
        return api_response(False, {}, "Failed to send payment reminders", 500, {"error": str(exc)})


@reminder_bp.get("/settings")
def reminder_settings_route():
    """Return reminder settings and history."""
    try:
        return api_response(True, get_reminder_settings(getattr(g, "current_user", {}) or {}), "Reminder settings fetched successfully")
    except Exception as exc:
        logger.exception("Reminder settings fetch failed")
        return api_response(False, {}, "Failed to fetch reminder settings", 500, {"error": str(exc)})


@reminder_bp.put("/settings")
def update_reminder_settings_route():
    """Update reminder settings."""
    try:
        return api_response(
            True,
            update_reminder_settings(request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {}),
            "Reminder settings updated successfully",
        )
    except Exception as exc:
        logger.exception("Reminder settings update failed")
        return api_response(False, {}, "Failed to update reminder settings", 500, {"error": str(exc)})


@reminder_bp.post("/run-auto")
def run_auto_reminders_route():
    """Run the auto reminder scheduler hook."""
    try:
        return api_response(True, run_auto_reminders(getattr(g, "current_user", {}) or {}), "Auto reminders processed successfully")
    except Exception as exc:
        logger.exception("Auto reminder run failed")
        return api_response(False, {}, "Failed to run auto reminders", 500, {"error": str(exc)})

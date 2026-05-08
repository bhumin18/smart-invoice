"""Recurring invoice API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.recurring_service import (
    create_recurring_profile,
    delete_recurring_profile,
    get_recurring_profiles,
    run_due_recurring,
    update_recurring_profile,
)
from utils.helpers import ValidationError, api_response


recurring_bp = Blueprint("recurring_routes", __name__, url_prefix="/api/recurring-invoices")
logger = logging.getLogger(__name__)


@recurring_bp.get("")
def list_recurring_route():
    """List recurring invoice profiles."""
    try:
        return api_response(True, get_recurring_profiles(getattr(g, "current_user", {}) or {}), "Recurring invoices fetched successfully")
    except Exception as exc:
        logger.exception("Recurring invoice listing failed")
        return api_response(False, {}, "Failed to fetch recurring invoices", 500, {"error": str(exc)})


@recurring_bp.post("")
def create_recurring_route():
    """Create a recurring invoice profile."""
    try:
        return api_response(
            True,
            create_recurring_profile(request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {}),
            "Recurring invoice created successfully",
            201,
        )
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Recurring invoice creation failed")
        return api_response(False, {}, "Failed to create recurring invoice", 500, {"error": str(exc)})


@recurring_bp.put("/<int:recurring_id>")
def update_recurring_route(recurring_id: int):
    """Update recurring invoice profile."""
    try:
        profile = update_recurring_profile(recurring_id, request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {})
        if profile is None:
            return api_response(False, {}, "Recurring invoice not found", 404)
        return api_response(True, profile, "Recurring invoice updated successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Recurring invoice update failed")
        return api_response(False, {}, "Failed to update recurring invoice", 500, {"error": str(exc)})


@recurring_bp.delete("/<int:recurring_id>")
def delete_recurring_route(recurring_id: int):
    """Delete recurring invoice profile."""
    try:
        if not delete_recurring_profile(recurring_id, getattr(g, "current_user", {}) or {}):
            return api_response(False, {}, "Recurring invoice not found", 404)
        return api_response(True, {"id": recurring_id}, "Recurring invoice deleted successfully")
    except Exception as exc:
        logger.exception("Recurring invoice delete failed")
        return api_response(False, {}, "Failed to delete recurring invoice", 500, {"error": str(exc)})


@recurring_bp.post("/run-due")
def run_due_recurring_route():
    """Generate invoices for due recurring profiles."""
    try:
        return api_response(True, run_due_recurring(getattr(g, "current_user", {}) or {}), "Due recurring invoices processed successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Recurring invoice run failed")
        return api_response(False, {}, "Failed to process recurring invoices", 500, {"error": str(exc)})

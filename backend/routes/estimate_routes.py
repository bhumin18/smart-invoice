"""Estimate and quotation API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.estimate_service import (
    convert_estimate_to_invoice,
    create_estimate,
    delete_estimate,
    get_estimate,
    get_estimates,
    update_estimate,
)
from utils.helpers import ValidationError, api_response


estimate_bp = Blueprint("estimate_routes", __name__, url_prefix="/api/estimates")
logger = logging.getLogger(__name__)


@estimate_bp.get("")
def list_estimates_route():
    """List estimates."""
    try:
        return api_response(True, get_estimates(getattr(g, "current_user", {}) or {}), "Estimates fetched successfully")
    except Exception as exc:
        logger.exception("Estimate listing failed")
        return api_response(False, {}, "Failed to fetch estimates", 500, {"error": str(exc)})


@estimate_bp.post("")
def create_estimate_route():
    """Create an estimate."""
    try:
        return api_response(
            True,
            create_estimate(request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {}),
            "Estimate created successfully",
            201,
        )
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Estimate creation failed")
        return api_response(False, {}, "Failed to create estimate", 500, {"error": str(exc)})


@estimate_bp.get("/<int:estimate_id>")
def get_estimate_route(estimate_id: int):
    """Fetch one estimate."""
    try:
        estimate = get_estimate(estimate_id, getattr(g, "current_user", {}) or {})
        if estimate is None:
            return api_response(False, {}, "Estimate not found", 404)
        return api_response(True, estimate, "Estimate fetched successfully")
    except Exception as exc:
        logger.exception("Estimate fetch failed")
        return api_response(False, {}, "Failed to fetch estimate", 500, {"error": str(exc)})


@estimate_bp.put("/<int:estimate_id>")
def update_estimate_route(estimate_id: int):
    """Update one estimate."""
    try:
        estimate = update_estimate(estimate_id, request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {})
        if estimate is None:
            return api_response(False, {}, "Estimate not found", 404)
        return api_response(True, estimate, "Estimate updated successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Estimate update failed")
        return api_response(False, {}, "Failed to update estimate", 500, {"error": str(exc)})


@estimate_bp.delete("/<int:estimate_id>")
def delete_estimate_route(estimate_id: int):
    """Delete one estimate."""
    try:
        if not delete_estimate(estimate_id, getattr(g, "current_user", {}) or {}):
            return api_response(False, {}, "Estimate not found", 404)
        return api_response(True, {"id": estimate_id}, "Estimate deleted successfully")
    except Exception as exc:
        logger.exception("Estimate delete failed")
        return api_response(False, {}, "Failed to delete estimate", 500, {"error": str(exc)})


@estimate_bp.post("/<int:estimate_id>/convert")
def convert_estimate_route(estimate_id: int):
    """Convert an estimate to an invoice."""
    try:
        invoice = convert_estimate_to_invoice(estimate_id, getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Estimate not found", 404)
        return api_response(True, invoice, "Estimate converted to invoice successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Estimate conversion failed")
        return api_response(False, {}, "Failed to convert estimate", 500, {"error": str(exc)})


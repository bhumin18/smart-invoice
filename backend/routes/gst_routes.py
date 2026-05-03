"""GST report API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.gst_service import download_gst_report
from services.auth_service import require_permission
from utils.helpers import ValidationError, api_response
from utils.auth_context import user_scope

gst_bp = Blueprint("gst_routes", __name__, url_prefix="/api/reports")
logger = logging.getLogger(__name__)


@gst_bp.get("/gst")
def gst_report_route():
    """Generate and download a GST report for a month and year."""
    try:
        month = int(request.args.get("month", "0"))
        year = int(request.args.get("year", "0"))
    except ValueError:
        return api_response(False, {}, "month and year must be valid numbers", 400)

    if month < 1 or month > 12:
        return api_response(False, {}, "month must be between 1 and 12", 400)
    if year < 2000 or year > 2100:
        return api_response(False, {}, "year must be between 2000 and 2100", 400)

    try:
        require_permission(getattr(g, "current_user", {}) or {}, "can_export_data")
        response = download_gst_report(month, year, user_scope(getattr(g, "current_user", {}) or {}))
        if response is None:
            return api_response(False, {}, "No invoices found for selected period", 404)
        return response
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except Exception as exc:
        logger.exception("GST report generation failed")
        return api_response(False, {}, "Failed to generate GST report", 500, {"error": str(exc)})

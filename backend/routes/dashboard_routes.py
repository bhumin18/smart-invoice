"""Dashboard API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g

from services.dashboard_service import get_dashboard_summary
from utils.helpers import api_response


dashboard_bp = Blueprint("dashboard_routes", __name__, url_prefix="/api/dashboard")
logger = logging.getLogger(__name__)


@dashboard_bp.get("/summary")
def dashboard_summary_route():
    """Return invoice dashboard summary."""
    try:
        return api_response(
            True,
            get_dashboard_summary(getattr(g, "current_user", {}) or {}),
            "Dashboard summary fetched successfully",
        )
    except Exception as exc:
        logger.exception("Dashboard summary failed")
        return api_response(False, {}, "Failed to fetch dashboard summary", 500, {"error": str(exc)})

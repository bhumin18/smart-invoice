"""Full data export API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.auth_service import require_permission
from services.export_service import download_data_export
from utils.helpers import ValidationError, api_response


export_bp = Blueprint("export_routes", __name__, url_prefix="/api/exports")
logger = logging.getLogger(__name__)


@export_bp.get("/data")
def data_export_route():
    """Download full application data as JSON or Excel."""
    export_format = str(request.args.get("format", "xlsx")).strip().lower()
    if export_format not in {"xlsx", "excel", "json"}:
        return api_response(False, {}, "format must be xlsx or json", 400)
    try:
        require_permission(getattr(g, "current_user", {}) or {}, "can_export_data")
        normalized_format = "json" if export_format == "json" else "xlsx"
        return download_data_export(normalized_format)
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except Exception as exc:
        logger.exception("Data export failed")
        return api_response(False, {}, "Failed to export data", 500, {"error": str(exc)})

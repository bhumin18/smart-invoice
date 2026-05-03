"""Backup and restore API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.auth_service import require_permission
from services.backup_service import download_backup, restore_backup
from utils.helpers import ValidationError, api_response


backup_bp = Blueprint("backup_routes", __name__, url_prefix="/api/backups")
logger = logging.getLogger(__name__)


@backup_bp.get("/export")
def export_backup_route():
    """Download a full app backup zip."""
    try:
        require_permission(getattr(g, "current_user", {}) or {}, "can_export_data")
        return download_backup()
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Backup export failed")
        return api_response(False, {}, "Failed to export backup", 500, {"error": str(exc)})


@backup_bp.post("/restore")
def restore_backup_route():
    """Restore app data from a backup zip."""
    try:
        require_permission(getattr(g, "current_user", {}) or {}, "can_export_data")
        result = restore_backup(request.files.get("backup"))
        return api_response(True, result, "Backup restored successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Backup restore failed")
        return api_response(False, {}, "Failed to restore backup", 500, {"error": str(exc)})

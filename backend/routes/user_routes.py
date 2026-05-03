"""Admin user management routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.user_service import get_users, update_user
from utils.helpers import ValidationError, api_response


user_bp = Blueprint("user_routes", __name__, url_prefix="/api/users")
logger = logging.getLogger(__name__)


@user_bp.get("")
def list_users_route():
    """List users for admin management."""
    try:
        return api_response(True, get_users(getattr(g, "current_user", {}) or {}), "Users fetched successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except Exception as exc:
        logger.exception("User listing failed")
        return api_response(False, {}, "Failed to fetch users", 500, {"error": str(exc)})


@user_bp.put("/<int:user_id>")
def update_user_route(user_id: int):
    """Update user permissions."""
    try:
        user = update_user(getattr(g, "current_user", {}) or {}, user_id, request.get_json(silent=True) or {})
        if user is None:
            return api_response(False, {}, "User not found", 404)
        return api_response(True, user, "User updated successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403 if "permission" in exc.errors else 400, exc.errors)
    except Exception as exc:
        logger.exception("User update failed")
        return api_response(False, {}, "Failed to update user", 500, {"error": str(exc)}
        )

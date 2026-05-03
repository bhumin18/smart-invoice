"""Authentication API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.auth_service import auth_enabled, change_password, forgot_password, login, register, reset_password
from utils.helpers import ValidationError, api_response


auth_bp = Blueprint("auth_routes", __name__, url_prefix="/api/auth")
logger = logging.getLogger(__name__)


@auth_bp.post("/login")
def login_route():
    """Authenticate admin user and return a bearer token."""
    try:
        result = login(request.get_json(silent=True) or {})
        return api_response(True, result, "Logged in successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 401, exc.errors)
    except Exception as exc:
        logger.exception("Login failed")
        return api_response(False, {}, "Login failed", 500, {"error": str(exc)})


@auth_bp.post("/register")
def register_route():
    """Create a new user account."""
    try:
        return api_response(True, register(request.get_json(silent=True) or {}), "Account created successfully", 201)
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Registration failed")
        return api_response(False, {}, "Registration failed", 500, {"error": str(exc)})


@auth_bp.post("/forgot-password")
def forgot_password_route():
    """Request a password reset token."""
    try:
        return api_response(True, forgot_password(request.get_json(silent=True) or {}), "Password reset requested")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Forgot password failed")
        return api_response(False, {}, "Password reset request failed", 500, {"error": str(exc)})


@auth_bp.post("/reset-password")
def reset_password_route():
    """Reset password with a reset token."""
    try:
        return api_response(True, reset_password(request.get_json(silent=True) or {}), "Password reset successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Reset password failed")
        return api_response(False, {}, "Password reset failed", 500, {"error": str(exc)})


@auth_bp.post("/change-password")
def change_password_route():
    """Change password for the current user."""
    try:
        return api_response(
            True,
            change_password(getattr(g, "current_user", {}) or {}, request.get_json(silent=True) or {}),
            "Password changed successfully",
        )
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Change password failed")
        return api_response(False, {}, "Password change failed", 500, {"error": str(exc)})


@auth_bp.get("/me")
def me_route():
    """Return current authenticated user."""
    if not auth_enabled():
        return api_response(True, {"username": "auth-disabled"}, "Authentication disabled")
    user = getattr(g, "current_user", None)
    if not user:
        return api_response(False, {}, "Unauthorized", 401)
    return api_response(True, {"user": user}, "Current user fetched successfully")

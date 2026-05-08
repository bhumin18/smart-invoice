"""Token based admin authentication service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash

from config import SECRET_KEY, get_config
from models.user_model import (
    get_user_by_email,
    get_user_by_reset_token,
    get_user_by_username,
    insert_user,
    set_reset_token,
    set_verification_token,
    update_password,
    user_count,
    verify_email_token,
)
from models.settings_model import registration_enabled
from utils.helpers import ValidationError


AUTH_SALT = "smart-invoice-auth"


def auth_enabled() -> bool:
    """Return whether admin authentication is enabled."""
    return bool(get_config("auth.enabled", True))


def _serializer() -> URLSafeTimedSerializer:
    """Create a token serializer."""
    return URLSafeTimedSerializer(SECRET_KEY, salt=AUTH_SALT)


def login(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate admin credentials and return an access token."""
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    user = get_user_by_username(username)
    if user is None or not int(user.get("active", 0)) or not check_password_hash(str(user.get("password_hash")), password):
        raise ValidationError({"credentials": "Invalid username or password"})

    expiry_hours = int(get_config("auth.token_expiry_hours", 24))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    token = _serializer().dumps({"id": user.get("id"), "username": user.get("username"), "role": user.get("role")})
    return {
        "token": token,
        "token_type": "Bearer",
        "expires_at": expires_at.isoformat(),
        "user": public_user(user),
    }


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify a bearer token and return the user payload."""
    if not auth_enabled():
        return {"username": "auth-disabled"}
    expiry_seconds = int(get_config("auth.token_expiry_hours", 24)) * 3600
    try:
        payload = _serializer().loads(token, max_age=expiry_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    user = get_user_by_username(str(payload.get("username", "")))
    if user is None or not bool(user.get("active", True)):
        return None
    return public_user(user)


def register(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a user account when registration is allowed."""
    if not registration_enabled() and user_count() > 0:
        raise ValidationError({"registration": "Account registration is disabled"})
    username = str(payload.get("username", "")).strip()
    email = str(payload.get("email", "")).strip()
    password = str(payload.get("password", ""))
    errors: dict[str, str] = {}
    if len(username) < 3:
        errors["username"] = "Username must be at least 3 characters"
    if email and "@" not in email:
        errors["email"] = "Email address is invalid"
    if len(password) < 6:
        errors["password"] = "Password must be at least 6 characters"
    if username and get_user_by_username(username):
        errors["username"] = "Username already exists"
    if email and get_user_by_email(email):
        errors["email"] = "Email already exists"
    if errors:
        raise ValidationError(errors)
    user = insert_user(username, email, password, role="user")
    result = public_user(user)
    if email:
        token = secrets.token_urlsafe(32)
        set_verification_token(int(user["id"]), token)
        if str(get_config("app.environment", "development")).lower() != "production":
            result["verification_token"] = token
            result["verification_link"] = f"{str(get_config('auth.password_reset_url', 'http://localhost:5173')).rstrip('/')}/?verify_email={token}"
    return result


def verify_email(payload: dict[str, Any]) -> dict[str, Any]:
    """Verify user email address by token."""
    token = str(payload.get("token", "")).strip()
    if not token:
        raise ValidationError({"token": "Verification token is required"})
    user = verify_email_token(token)
    if user is None:
        raise ValidationError({"token": "Verification token is invalid"})
    return public_user(user)


def forgot_password(payload: dict[str, Any]) -> dict[str, Any]:
    """Create a password reset token for an existing user."""
    identifier = str(payload.get("email") or payload.get("username") or "").strip()
    if not identifier:
        raise ValidationError({"email": "Email or username is required"})
    user = get_user_by_email(identifier) if "@" in identifier else get_user_by_username(identifier)
    if user is None:
        return {"sent": True}
    token = secrets.token_urlsafe(32)
    expiry_minutes = int(get_config("auth.password_reset_token_minutes", 30))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)).isoformat()
    set_reset_token(int(user["id"]), token, expires_at)
    reset_base = str(get_config("auth.password_reset_url", "http://localhost:5173")).rstrip("/")
    reset_link = f"{reset_base}?reset_token={token}"
    email_enabled = bool(get_config("email.enabled", False))
    if email_enabled:
        from services.email_service import send_password_reset_email

        send_password_reset_email(user, reset_link)
        return {"sent": True, "expires_at": expires_at}

    result = {"sent": True, "expires_at": expires_at}
    if str(get_config("app.environment", "development")).lower() != "production":
        result.update(
            {
                "reset_token": token,
                "reset_link": reset_link,
                "note": "Development mode only: configure SMTP to email reset links and hide tokens.",
            }
        )
    return result


def reset_password(payload: dict[str, Any]) -> dict[str, Any]:
    """Reset password using a reset token."""
    token = str(payload.get("token", "")).strip()
    password = str(payload.get("password", ""))
    if not token:
        raise ValidationError({"token": "Reset token is required"})
    if len(password) < 6:
        raise ValidationError({"password": "Password must be at least 6 characters"})
    user = get_user_by_reset_token(token)
    if user is None:
        raise ValidationError({"token": "Reset token is invalid"})
    expires_at = datetime.fromisoformat(str(user.get("reset_expires_at")))
    if expires_at < datetime.now(timezone.utc):
        raise ValidationError({"token": "Reset token has expired"})
    update_password(int(user["id"]), password)
    return {"reset": True}


def change_password(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Change password for the current authenticated user."""
    current_password = str(payload.get("current_password", ""))
    new_password = str(payload.get("new_password", ""))
    db_user = get_user_by_username(str(user.get("username", "")))
    if db_user is None or not check_password_hash(str(db_user.get("password_hash")), current_password):
        raise ValidationError({"current_password": "Current password is incorrect"})
    if len(new_password) < 6:
        raise ValidationError({"new_password": "New password must be at least 6 characters"})
    update_password(int(db_user["id"]), new_password)
    return {"changed": True}


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    """Return a safe user payload."""
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "active": bool(user.get("active", True)),
        "can_create_invoices": bool(user.get("can_create_invoices", True)),
        "can_manage_company": bool(user.get("can_manage_company", True)),
        "can_export_data": bool(user.get("can_export_data", True)),
        "email_verified": bool(user.get("email_verified", False)),
    }


def require_admin(user: dict[str, Any]) -> None:
    """Raise validation error unless the current user is an admin."""
    if str(user.get("role", "")).lower() != "admin":
        raise ValidationError({"permission": "Admin permission is required"})


def require_permission(user: dict[str, Any], permission: str) -> None:
    """Raise validation error unless the user has a named permission."""
    if str(user.get("role", "")).lower() == "admin":
        return
    if not bool(user.get(permission, False)):
        raise ValidationError({"permission": "You do not have permission for this action"})

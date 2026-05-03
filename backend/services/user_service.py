"""Admin user management service."""

from __future__ import annotations

from typing import Any

from models.user_model import list_users, update_user_record
from services.auth_service import public_user, require_admin
from utils.helpers import ValidationError


def get_users(current_user: dict[str, Any]) -> list[dict[str, Any]]:
    """Return users for admins."""
    require_admin(current_user)
    return [public_user(user) for user in list_users()]


def update_user(current_user: dict[str, Any], user_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Update user role, active state, and permissions."""
    require_admin(current_user)
    role = str(payload.get("role", "user")).lower()
    if role not in {"admin", "user"}:
        raise ValidationError({"role": "Role must be admin or user"})
    updated = update_user_record(
        user_id,
        {
            "role": role,
            "active": bool(payload.get("active", True)),
            "can_create_invoices": bool(payload.get("can_create_invoices", True)),
            "can_manage_company": bool(payload.get("can_manage_company", True)),
            "can_export_data": bool(payload.get("can_export_data", True)),
        },
    )
    return public_user(updated) if updated else None

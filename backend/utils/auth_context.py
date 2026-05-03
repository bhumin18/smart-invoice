"""Helpers for request user scoping."""

from __future__ import annotations

from typing import Any


def is_admin(user: dict[str, Any] | None) -> bool:
    """Return whether the current user is an admin."""
    return str((user or {}).get("role", "")).lower() == "admin"


def user_scope(user: dict[str, Any] | None) -> dict[str, Any]:
    """Return ownership filter scope for data queries."""
    user = user or {}
    return {
        "owner_user_id": user.get("id"),
        "include_all": is_admin(user),
    }

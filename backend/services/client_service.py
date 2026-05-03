"""Business logic for client master records."""

from __future__ import annotations

import logging
from typing import Any

from models.client_model import (
    delete_client_record,
    get_client_by_id,
    insert_client,
    list_clients,
    update_client_record,
)
from utils.auth_context import user_scope
from utils.helpers import ValidationError


logger = logging.getLogger(__name__)


def validate_client_payload(payload: dict[str, Any]) -> dict[str, str]:
    """Validate client master payload."""
    errors: dict[str, str] = {}
    if not str(payload.get("name", "")).strip():
        errors["name"] = "Client name is required"
    email = str(payload.get("email", "")).strip()
    if email and "@" not in email:
        errors["email"] = "Email address is invalid"
    return errors


def normalize_client_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a client payload for persistence."""
    errors = validate_client_payload(payload)
    if errors:
        raise ValidationError(errors)
    return {
        "name": str(payload.get("name", "")).strip(),
        "gstin": str(payload.get("gstin", "")).strip().upper(),
        "address": str(payload.get("address", "")).strip(),
        "state": str(payload.get("state", "")).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "email": str(payload.get("email", "")).strip(),
        "notes": str(payload.get("notes", "")).strip(),
    }


def get_clients(search: str = "", current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return client master records."""
    return list_clients(search, **user_scope(current_user))


def get_client(client_id: int, current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return one client by ID."""
    return get_client_by_id(client_id, **user_scope(current_user))


def create_client(payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a client master record."""
    normalized = normalize_client_payload(payload)
    normalized["owner_user_id"] = (current_user or {}).get("id")
    client = insert_client(normalized)
    logger.info("Created client %s", client.get("name"))
    return client


def update_client(client_id: int, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Update a client master record."""
    current = get_client_by_id(client_id, **user_scope(current_user))
    if current is None:
        return None
    client = update_client_record(client_id, normalize_client_payload({**current, **payload}))
    if client:
        logger.info("Updated client %s", client.get("name"))
    return client


def delete_client(client_id: int, current_user: dict[str, Any] | None = None) -> bool:
    """Delete a client master record."""
    deleted = delete_client_record(client_id, **user_scope(current_user))
    if deleted:
        logger.info("Deleted client id=%s", client_id)
    return deleted

"""Audit logging service."""

from __future__ import annotations

import logging
from typing import Any

from models.audit_model import get_audit_logs, insert_audit_log
from utils.auth_context import user_scope


logger = logging.getLogger(__name__)


def record_audit(
    action: str,
    entity_type: str,
    entity_id: int | None,
    current_user: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
    owner_user_id: int | None = None,
) -> None:
    """Record an audit event without breaking the main workflow if logging fails."""
    user = current_user or {}
    try:
        insert_audit_log(
            owner_user_id=owner_user_id if owner_user_id is not None else user.get("id"),
            actor_user_id=user.get("id"),
            actor_username=str(user.get("username") or ""),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    except Exception:
        logger.exception("Failed to record audit event action=%s entity=%s id=%s", action, entity_type, entity_id)


def list_invoice_audit(invoice_id: int, current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return audit entries for one invoice."""
    return get_audit_logs(entity_type="invoice", entity_id=invoice_id, **user_scope(current_user), limit=100)

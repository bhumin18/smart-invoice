"""Admin dashboard helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from models.audit_model import get_audit_logs
from models.invoice_model import get_all_invoice_attachments, get_invoices, get_public_link_invoices
from models.job_model import list_job_logs
from models.security_model import list_auth_events
from models.settings_model import registration_enabled, set_setting
from models.user_model import list_users
from services.auth_service import require_admin
from utils.helpers import DATABASE_PATH, OUTPUT_DIR


def _folder_size(path: Path) -> int:
    """Return folder size in bytes."""
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def get_admin_overview(current_user: dict[str, Any]) -> dict[str, Any]:
    """Return admin-level app overview."""
    require_admin(current_user)
    users = list_users()
    invoices = get_invoices({"include_all": True})
    invoice_counts: dict[str, int] = {}
    for invoice in invoices:
        owner = str(invoice.get("owner_user_id") or "unknown")
        invoice_counts[owner] = invoice_counts.get(owner, 0) + 1
    return {
        "total_users": len(users),
        "active_users": sum(1 for user in users if bool(user.get("active"))),
        "total_invoices": len(invoices),
        "registration_enabled": registration_enabled(),
        "storage": {
            "database_bytes": DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0,
            "outputs_bytes": _folder_size(OUTPUT_DIR),
        },
        "invoices_by_user": invoice_counts,
        "recent_activity": get_audit_logs(include_all=True, limit=25),
        "login_activity": list_auth_events(25),
        "job_logs": list_job_logs(25),
        "public_links": get_public_link_invoices(25),
        "uploads": get_all_invoice_attachments(25),
    }


def update_admin_settings(current_user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Update admin runtime settings."""
    require_admin(current_user)
    if "registration_enabled" in payload:
        set_setting("auth.allow_registration", "true" if bool(payload["registration_enabled"]) else "false")
    return get_admin_overview(current_user)

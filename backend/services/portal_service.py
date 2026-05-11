"""Client portal and invoice attachment service."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models.invoice_model import (
    get_invoice_by_id,
    get_invoice_by_public_token,
    insert_invoice_attachment,
    revoke_invoice_public_link,
    set_invoice_payment_proof,
    update_client_portal_message,
    update_invoice_public_link,
    update_payment_proof_status,
)
from config import get_config
from services.pdf_service import generate_invoice_pdf
from utils.auth_context import user_scope
from utils.helpers import ASSETS_OUTPUT_DIR, ValidationError, ensure_directories


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx"}


def _portal_link_payload(invoice: dict[str, Any], token: str) -> dict[str, Any]:
    """Return public link metadata."""
    return {
        "token": token,
        "public_path": f"/portal/{token}",
        "invoice_id": invoice.get("id"),
        "expires_at": invoice.get("public_token_expires_at", ""),
        "revoked_at": invoice.get("public_token_revoked_at", ""),
    }


def _public_link_active(invoice: dict[str, Any]) -> bool:
    """Return whether public portal access is currently allowed."""
    if str(invoice.get("public_token_revoked_at") or "").strip():
        return False
    expires_at = str(invoice.get("public_token_expires_at") or "")
    if not expires_at:
        return True
    try:
        return datetime.fromisoformat(expires_at) >= datetime.now()
    except ValueError:
        return False


def create_or_get_public_link(invoice_id: int, current_user: dict[str, Any], expiry_days: int | None = None) -> dict[str, Any] | None:
    """Create or return a stable public client portal token for an invoice."""
    invoice = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if invoice is None:
        return None
    token = str(invoice.get("public_token") or "")
    if not token or not _public_link_active(invoice):
        token = secrets.token_urlsafe(24)
        days = int(expiry_days or get_config("portal.default_link_expiry_days", 30))
        invoice = update_invoice_public_link(
            invoice_id,
            token,
            (date.today() + timedelta(days=max(1, days))).isoformat(),
            "",
        ) or invoice
    return _portal_link_payload(invoice, token)


def revoke_public_link(invoice_id: int, current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Revoke one invoice public portal link."""
    invoice = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if invoice is None:
        return None
    return revoke_invoice_public_link(invoice_id)


def get_public_invoice(token: str) -> dict[str, Any] | None:
    """Return a public-safe invoice payload by token."""
    invoice = get_invoice_by_public_token(token)
    if invoice is None or not _public_link_active(invoice):
        return None
    return {
        "invoice_number": invoice.get("invoice_number"),
        "client_name": invoice.get("client_name"),
        "date": invoice.get("date"),
        "due_date": invoice.get("due_date"),
        "subtotal": invoice.get("subtotal"),
        "gst_amount": invoice.get("gst_amount"),
        "total": invoice.get("total"),
        "amount_paid": invoice.get("amount_paid"),
        "balance_due": invoice.get("balance_due"),
        "status": invoice.get("status"),
        "payment_proof_status": invoice.get("payment_proof_status"),
        "client_portal_message": invoice.get("client_portal_message"),
        "timeline": [
            {"label": "Invoice created", "date": invoice.get("created_at")},
            *[
                {"label": f"Payment received: {payment.get('amount')}", "date": payment.get("date")}
                for payment in invoice.get("payments", [])
            ],
        ],
        "items": invoice.get("items", []),
    }


def generate_public_invoice_pdf(token: str) -> str | None:
    """Generate PDF for public invoice portal."""
    invoice = get_invoice_by_public_token(token)
    if invoice is None or not _public_link_active(invoice):
        return None
    return generate_invoice_pdf(invoice)


def _save_upload(file: FileStorage, folder: Path, prefix: str) -> Path:
    """Validate and save an uploaded file."""
    if file is None or not file.filename:
        raise ValidationError({"file": "File is required"})
    max_bytes = int(get_config("security.max_upload_mb", 10)) * 1024 * 1024
    if file.content_length and int(file.content_length) > max_bytes:
        raise ValidationError({"file": f"File must be {get_config('security.max_upload_mb', 10)} MB or smaller"})
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError({"file": "Unsupported file type"})
    ensure_directories()
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(file.filename)
    path = folder / f"{prefix}_{secrets.token_hex(6)}_{safe_name}"
    file.save(path)
    return path


def upload_invoice_attachment(
    invoice_id: int,
    file: FileStorage,
    current_user: dict[str, Any],
    attachment_type: str = "supporting",
) -> dict[str, Any] | None:
    """Upload a private invoice attachment."""
    invoice = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if invoice is None or not _public_link_active(invoice):
        return None
    path = _save_upload(file, ASSETS_OUTPUT_DIR / "attachments", f"invoice_{invoice_id}")
    return insert_invoice_attachment(
        invoice_id,
        invoice.get("owner_user_id"),
        Path(path).name,
        str(path),
        attachment_type,
    )


def upload_payment_proof(token: str, file: FileStorage) -> dict[str, Any] | None:
    """Upload a client payment proof from the public portal."""
    invoice = get_invoice_by_public_token(token)
    if invoice is None:
        return None
    path = _save_upload(file, ASSETS_OUTPUT_DIR / "payment_proofs", f"invoice_{invoice['id']}")
    updated = set_invoice_payment_proof(int(invoice["id"]), str(path))
    return {"uploaded": True, "invoice_number": updated.get("invoice_number") if updated else ""}


def save_client_message(token: str, message: str) -> dict[str, Any] | None:
    """Save a client message from the public portal."""
    invoice = get_invoice_by_public_token(token)
    if invoice is None or not _public_link_active(invoice):
        return None
    clean_message = str(message or "").strip()
    if not clean_message:
        raise ValidationError({"message": "Message is required"})
    if len(clean_message) > 1000:
        raise ValidationError({"message": "Message must be 1000 characters or fewer"})
    update_client_portal_message(int(invoice["id"]), clean_message)
    return {"saved": True, "invoice_number": invoice.get("invoice_number")}


def review_payment_proof(invoice_id: int, status: str, current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Approve or reject a client payment proof."""
    invoice = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if invoice is None:
        return None
    normalized = str(status or "").strip().lower().replace(" ", "_")
    if normalized not in {"approved", "rejected", "pending_review"}:
        raise ValidationError({"status": "Status must be approved, rejected, or pending_review"})
    return update_payment_proof_status(invoice_id, normalized)

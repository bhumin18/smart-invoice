"""Client portal and invoice attachment service."""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models.invoice_model import (
    get_invoice_by_id,
    get_invoice_by_public_token,
    insert_invoice_attachment,
    set_invoice_payment_proof,
    set_invoice_public_token,
)
from services.pdf_service import generate_invoice_pdf
from utils.auth_context import user_scope
from utils.helpers import ASSETS_OUTPUT_DIR, ValidationError, ensure_directories


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx"}


def create_or_get_public_link(invoice_id: int, current_user: dict[str, Any]) -> dict[str, Any] | None:
    """Create or return a stable public client portal token for an invoice."""
    invoice = get_invoice_by_id(invoice_id, **user_scope(current_user))
    if invoice is None:
        return None
    token = str(invoice.get("public_token") or "")
    if not token:
        token = secrets.token_urlsafe(24)
        set_invoice_public_token(invoice_id, token)
    return {"token": token, "public_path": f"/portal/{token}", "invoice_id": invoice_id}


def get_public_invoice(token: str) -> dict[str, Any] | None:
    """Return a public-safe invoice payload by token."""
    invoice = get_invoice_by_public_token(token)
    if invoice is None:
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
        "items": invoice.get("items", []),
    }


def generate_public_invoice_pdf(token: str) -> str | None:
    """Generate PDF for public invoice portal."""
    invoice = get_invoice_by_public_token(token)
    if invoice is None:
        return None
    return generate_invoice_pdf(invoice)


def _save_upload(file: FileStorage, folder: Path, prefix: str) -> Path:
    """Validate and save an uploaded file."""
    if file is None or not file.filename:
        raise ValidationError({"file": "File is required"})
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
    if invoice is None:
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

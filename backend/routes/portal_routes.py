"""Client portal and attachment routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request, send_file

from services.portal_service import (
    create_or_get_public_link,
    generate_public_invoice_pdf,
    get_public_invoice,
    upload_invoice_attachment,
    upload_payment_proof,
)
from utils.helpers import ValidationError, api_response


portal_bp = Blueprint("portal_routes", __name__)
logger = logging.getLogger(__name__)


@portal_bp.post("/api/invoices/<int:invoice_id>/public-link")
def invoice_public_link_route(invoice_id: int):
    """Create or return a public portal link for one invoice."""
    try:
        link = create_or_get_public_link(invoice_id, getattr(g, "current_user", {}) or {})
        if link is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, link, "Public link fetched successfully")
    except Exception as exc:
        logger.exception("Public link generation failed")
        return api_response(False, {}, "Failed to create public link", 500, {"error": str(exc)})


@portal_bp.post("/api/invoices/<int:invoice_id>/attachments")
def invoice_attachment_route(invoice_id: int):
    """Upload private invoice attachment."""
    try:
        attachment = upload_invoice_attachment(
            invoice_id,
            request.files.get("file"),
            getattr(g, "current_user", {}) or {},
            str(request.form.get("type") or "supporting"),
        )
        if attachment is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, attachment, "Attachment uploaded successfully", 201)
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Attachment upload failed")
        return api_response(False, {}, "Failed to upload attachment", 500, {"error": str(exc)})


@portal_bp.get("/api/portal/<token>")
def public_invoice_route(token: str):
    """Return public invoice details."""
    invoice = get_public_invoice(token)
    if invoice is None:
        return api_response(False, {}, "Invoice not found", 404)
    return api_response(True, invoice, "Invoice fetched successfully")


@portal_bp.get("/api/portal/<token>/pdf")
def public_invoice_pdf_route(token: str):
    """Download public invoice PDF."""
    path = generate_public_invoice_pdf(token)
    if path is None:
        return api_response(False, {}, "Invoice not found", 404)
    return send_file(path, as_attachment=True)


@portal_bp.post("/api/portal/<token>/payment-proof")
def public_payment_proof_route(token: str):
    """Upload public payment proof."""
    try:
        result = upload_payment_proof(token, request.files.get("file"))
        if result is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, result, "Payment proof uploaded successfully", 201)
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Payment proof upload failed")
        return api_response(False, {}, "Failed to upload payment proof", 500, {"error": str(exc)})

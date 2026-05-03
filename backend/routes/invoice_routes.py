"""Invoice API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.invoice_service import (
    clone_invoice,
    create_invoice,
    get_invoice,
    list_invoices,
    record_payment,
    remove_invoice,
    update_invoice,
    void_invoice,
)
from services.email_service import send_invoice_email
from services.pdf_service import download_invoice_pdf, download_receipt_pdf
from services.numbering_service import preview_next_invoice_number
from utils.helpers import ValidationError, api_response
from utils.auth_context import user_scope

invoice_bp = Blueprint("invoice_routes", __name__, url_prefix="/api/invoices")
logger = logging.getLogger(__name__)


@invoice_bp.post("")
def create_invoice_route():
    """Create an invoice from JSON payload."""
    payload = request.get_json(silent=True) or {}
    try:
        invoice = create_invoice(payload, getattr(g, "current_user", {}) or {})
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except ValueError as exc:
        return api_response(False, {}, str(exc), 400)
    except Exception as exc:
        logger.exception("Invoice creation failed")
        return api_response(False, {}, "Failed to create invoice", 500, {"error": str(exc)})
    return api_response(True, invoice, "Invoice created successfully", 201)


@invoice_bp.get("")
def list_invoices_route():
    """List all invoices."""
    try:
        filters = {
            "status": request.args.get("status", ""),
            "client": request.args.get("client", ""),
            "search": request.args.get("search", ""),
            "date_from": request.args.get("date_from", ""),
            "date_to": request.args.get("date_to", ""),
        }
        filters.update(user_scope(getattr(g, "current_user", {}) or {}))
        return api_response(True, list_invoices(filters), "Invoices fetched successfully")
    except Exception as exc:
        logger.exception("Invoice listing failed")
        return api_response(False, {}, "Failed to fetch invoices", 500, {"error": str(exc)})


@invoice_bp.get("/next-number")
def next_invoice_number_route():
    """Preview the next invoice number without incrementing it."""
    try:
        return api_response(
            True,
            {"invoice_number": preview_next_invoice_number((getattr(g, "current_user", {}) or {}).get("id"))},
            "Next invoice number fetched successfully",
        )
    except Exception as exc:
        logger.exception("Invoice number preview failed")
        return api_response(False, {}, "Failed to fetch next invoice number", 500, {"error": str(exc)})


@invoice_bp.get("/<int:invoice_id>")
def get_invoice_route(invoice_id: int):
    """Fetch one invoice by ID."""
    try:
        invoice = get_invoice(invoice_id, getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, invoice, "Invoice fetched successfully")
    except Exception as exc:
        logger.exception("Invoice fetch failed for id=%s", invoice_id)
        return api_response(False, {}, "Failed to fetch invoice", 500, {"error": str(exc)})


@invoice_bp.put("/<int:invoice_id>")
def update_invoice_route(invoice_id: int):
    """Update one invoice by ID."""
    payload = request.get_json(silent=True) or {}
    try:
        invoice = update_invoice(invoice_id, payload, getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, invoice, "Invoice updated successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except ValueError as exc:
        return api_response(False, {}, str(exc), 400)
    except Exception as exc:
        logger.exception("Invoice update failed for id=%s", invoice_id)
        return api_response(False, {}, "Failed to update invoice", 500, {"error": str(exc)})


@invoice_bp.delete("/<int:invoice_id>")
def delete_invoice_route(invoice_id: int):
    """Delete one invoice by ID."""
    try:
        if not remove_invoice(invoice_id, getattr(g, "current_user", {}) or {}):
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, {"id": invoice_id}, "Invoice deleted successfully")
    except Exception as exc:
        logger.exception("Invoice delete failed for id=%s", invoice_id)
        return api_response(False, {}, "Failed to delete invoice", 500, {"error": str(exc)})


@invoice_bp.get("/<int:invoice_id>/pdf")
def invoice_pdf_route(invoice_id: int):
    """Generate and download one invoice PDF."""
    try:
        invoice = get_invoice(invoice_id, getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        return download_invoice_pdf(invoice)
    except Exception as exc:
        logger.exception("PDF generation failed for invoice id=%s", invoice_id)
        return api_response(False, {}, "Failed to generate invoice PDF", 500, {"error": str(exc)})


@invoice_bp.get("/<int:invoice_id>/payments/<int:payment_id>/receipt")
def payment_receipt_route(invoice_id: int, payment_id: int):
    """Generate and download a payment receipt PDF."""
    try:
        invoice = get_invoice(invoice_id, getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        response = download_receipt_pdf(invoice, payment_id)
        if response is None:
            return api_response(False, {}, "Payment not found", 404)
        return response
    except Exception as exc:
        logger.exception("Receipt generation failed for invoice id=%s payment id=%s", invoice_id, payment_id)
        return api_response(False, {}, "Failed to generate receipt PDF", 500, {"error": str(exc)})


@invoice_bp.post("/<int:invoice_id>/email")
def invoice_email_route(invoice_id: int):
    """Email one invoice PDF to a recipient."""
    payload = request.get_json(silent=True) or {}
    try:
        invoice = get_invoice(invoice_id, getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        result = send_invoice_email(invoice, payload)
        return api_response(True, result, "Invoice emailed successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Invoice email failed for id=%s", invoice_id)
        return api_response(False, {}, "Failed to email invoice", 500, {"error": str(exc)})


@invoice_bp.post("/<int:invoice_id>/void")
def void_invoice_route(invoice_id: int):
    """Void one invoice by ID while keeping the record."""
    payload = request.get_json(silent=True) or {}
    try:
        invoice = void_invoice(invoice_id, str(payload.get("reason", "")), getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, invoice, "Invoice voided successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Invoice void failed for id=%s", invoice_id)
        return api_response(False, {}, "Failed to void invoice", 500, {"error": str(exc)})


@invoice_bp.post("/<int:invoice_id>/clone")
def clone_invoice_route(invoice_id: int):
    """Clone one invoice by ID into a new draft invoice."""
    try:
        invoice = clone_invoice(invoice_id, getattr(g, "current_user", {}) or {})
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, invoice, "Invoice cloned successfully", 201)
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Invoice clone failed for id=%s", invoice_id)
        return api_response(False, {}, "Failed to clone invoice", 500, {"error": str(exc)})


@invoice_bp.post("/<int:invoice_id>/payments")
def invoice_payment_route(invoice_id: int):
    """Record one payment against an invoice."""
    payload = request.get_json(silent=True) or {}
    try:
        invoice = record_payment(
            invoice_id,
            float(payload.get("amount", 0)),
            str(payload.get("date", "")),
            str(payload.get("mode", "")),
            str(payload.get("reference", "")),
            str(payload.get("notes", "")),
            getattr(g, "current_user", {}) or {},
        )
        if invoice is None:
            return api_response(False, {}, "Invoice not found", 404)
        return api_response(True, invoice, "Payment recorded successfully", 201)
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except ValueError as exc:
        return api_response(False, {}, str(exc), 400)
    except Exception as exc:
        logger.exception("Invoice payment failed for id=%s", invoice_id)
        return api_response(False, {}, "Failed to record payment", 500, {"error": str(exc)})

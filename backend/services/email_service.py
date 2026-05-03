"""Email delivery service for invoice PDFs."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from config import get_config
from models.company_model import get_company
from services.pdf_service import generate_invoice_pdf
from utils.helpers import ValidationError


logger = logging.getLogger(__name__)


def _email_config() -> dict[str, Any]:
    """Return email configuration."""
    return dict(get_config("email", {}) or {})


def send_invoice_email(invoice: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Generate invoice PDF and email it to the client."""
    config = _email_config()
    if not bool(config.get("enabled")):
        raise ValidationError({"email": "Email is disabled. Enable email.enabled in backend/config.yaml."})

    to_email = str(payload.get("to_email") or "").strip()
    if not to_email or "@" not in to_email:
        raise ValidationError({"to_email": "A valid recipient email is required"})

    from_email = str(config.get("from_email") or config.get("username") or "").strip()
    if not from_email:
        raise ValidationError({"from_email": "SMTP from_email or username is not configured"})

    company = get_company(invoice.get("owner_user_id"))
    subject = str(payload.get("subject") or f"Invoice {invoice.get('invoice_number')} from {company.get('name')}").strip()
    message = str(
        payload.get("message")
        or f"Dear {invoice.get('client_name')},\n\nPlease find attached invoice {invoice.get('invoice_number')}.\n\nThank you."
    )
    pdf_path = Path(generate_invoice_pdf(invoice))

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = f"{config.get('from_name') or company.get('name') or 'Smart Invoice'} <{from_email}>"
    email["To"] = to_email
    email.set_content(message)
    email.add_attachment(
        pdf_path.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=pdf_path.name,
    )

    host = str(config.get("smtp_host") or "").strip()
    port = int(config.get("smtp_port") or 587)
    username = str(config.get("username") or "").strip()
    password = str(config.get("password") or "")
    if not host:
        raise ValidationError({"smtp_host": "SMTP host is not configured"})

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if bool(config.get("use_tls", True)):
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(email)

    logger.info("Emailed invoice %s to %s", invoice.get("invoice_number"), to_email)
    return {"to_email": to_email, "subject": subject, "attachment": pdf_path.name}


def send_password_reset_email(user: dict[str, Any], reset_link: str) -> dict[str, Any]:
    """Email a password reset link to a user."""
    config = _email_config()
    if not bool(config.get("enabled")):
        raise ValidationError({"email": "Email is disabled. Enable email.enabled in backend/config.yaml."})

    to_email = str(user.get("email") or "").strip()
    if not to_email or "@" not in to_email:
        raise ValidationError({"email": "User does not have a valid email address"})

    from_email = str(config.get("from_email") or config.get("username") or "").strip()
    if not from_email:
        raise ValidationError({"from_email": "SMTP from_email or username is not configured"})

    email = EmailMessage()
    email["Subject"] = "Reset your Smart Invoice password"
    email["From"] = f"{config.get('from_name') or 'Smart Invoice'} <{from_email}>"
    email["To"] = to_email
    email.set_content(
        "We received a request to reset your Smart Invoice password.\n\n"
        f"Open this link to set a new password:\n{reset_link}\n\n"
        "If you did not request this, you can ignore this email."
    )

    host = str(config.get("smtp_host") or "").strip()
    port = int(config.get("smtp_port") or 587)
    username = str(config.get("username") or "").strip()
    password = str(config.get("password") or "")
    if not host:
        raise ValidationError({"smtp_host": "SMTP host is not configured"})

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if bool(config.get("use_tls", True)):
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(email)

    logger.info("Sent password reset email to user id=%s", user.get("id"))
    return {"to_email": to_email}

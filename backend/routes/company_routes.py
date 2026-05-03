"""Company settings API routes."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, g, request

from models.company_model import get_company, update_company
from services.auth_service import require_permission
from utils.helpers import ASSETS_OUTPUT_DIR, ValidationError, api_response, ensure_directories

company_bp = Blueprint("company_routes", __name__, url_prefix="/api/company")
logger = logging.getLogger(__name__)


@company_bp.get("")
def get_company_route():
    """Fetch company settings."""
    try:
        user = getattr(g, "current_user", {}) or {}
        return api_response(True, get_company(user.get("id")), "Company settings fetched successfully")
    except Exception as exc:
        logger.exception("Company settings fetch failed")
        return api_response(False, {}, "Failed to fetch company settings", 500, {"error": str(exc)})


@company_bp.post("")
def update_company_route():
    """Create or update company settings."""
    payload = request.get_json(silent=True) or {}
    try:
        require_permission(getattr(g, "current_user", {}) or {}, "can_manage_company")
        user = getattr(g, "current_user", {}) or {}
        company = update_company(payload, user.get("id"))
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except (TypeError, ValueError) as exc:
        return api_response(False, {}, str(exc), 400)
    except Exception as exc:
        logger.exception("Company settings save failed")
        return api_response(False, {}, "Failed to save company settings", 500, {"error": str(exc)})
    return api_response(True, company, "Company settings saved successfully")


@company_bp.post("/logo")
def upload_company_logo_route():
    """Upload a company logo and store its path in company settings."""
    try:
        require_permission(getattr(g, "current_user", {}) or {}, "can_manage_company")
        logo = request.files.get("logo")
        if logo is None or not logo.filename:
            return api_response(
                False,
                {},
                "Validation error",
                400,
                {"logo": "Logo file is required"},
            )
        suffix = Path(logo.filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            return api_response(
                False,
                {},
                "Validation error",
                400,
                {"logo": "Logo must be a PNG, JPG, or JPEG file"},
            )
        ensure_directories()
        user = getattr(g, "current_user", {}) or {}
        logo_path = ASSETS_OUTPUT_DIR / f"user_{user.get('id', 'default')}_company_logo{suffix}"
        logo.save(logo_path)
        company = update_company({"logo_path": str(logo_path)}, user.get("id"))
        logger.info("Company logo uploaded to %s", logo_path)
        return api_response(True, company, "Company logo uploaded successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except Exception as exc:
        logger.exception("Company logo upload failed")
        return api_response(False, {}, "Failed to upload company logo", 500, {"error": str(exc)})


@company_bp.post("/signature")
def upload_company_signature_route():
    """Upload an authorized signature image and store its path in company settings."""
    try:
        require_permission(getattr(g, "current_user", {}) or {}, "can_manage_company")
        signature = request.files.get("signature")
        if signature is None or not signature.filename:
            return api_response(
                False,
                {},
                "Validation error",
                400,
                {"signature": "Signature image is required"},
            )
        suffix = Path(signature.filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            return api_response(
                False,
                {},
                "Validation error",
                400,
                {"signature": "Signature must be a PNG, JPG, or JPEG file"},
            )
        ensure_directories()
        user = getattr(g, "current_user", {}) or {}
        signature_path = ASSETS_OUTPUT_DIR / f"user_{user.get('id', 'default')}_authorized_signature{suffix}"
        signature.save(signature_path)
        company = update_company({"signature_path": str(signature_path)}, user.get("id"))
        logger.info("Company authorized signature uploaded to %s", signature_path)
        return api_response(True, company, "Authorized signature uploaded successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except Exception as exc:
        logger.exception("Authorized signature upload failed")
        return api_response(False, {}, "Failed to upload authorized signature", 500, {"error": str(exc)})

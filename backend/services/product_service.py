"""Business logic for product and service master records."""

from __future__ import annotations

import logging
from typing import Any

from config import MAX_GST_RATE
from models.product_model import (
    delete_product_record,
    get_product_by_id,
    insert_product,
    list_products,
    update_product_record,
)
from utils.auth_context import user_scope
from utils.helpers import ValidationError


logger = logging.getLogger(__name__)


def validate_product_payload(payload: dict[str, Any]) -> dict[str, str]:
    """Validate product/service payload."""
    errors: dict[str, str] = {}
    if not str(payload.get("name", "")).strip():
        errors["name"] = "Product or service name is required"
    try:
        price = float(payload.get("price", 0))
        gst_rate = float(payload.get("gst_rate", 0))
        if price < 0:
            errors["price"] = "Price must be greater than or equal to zero"
        if gst_rate < 0 or gst_rate > MAX_GST_RATE:
            errors["gst_rate"] = f"GST rate must be between 0 and {MAX_GST_RATE:g}"
    except (TypeError, ValueError):
        errors["price"] = "Price and GST rate must be valid numbers"
    return errors


def normalize_product_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize a product/service payload for persistence."""
    errors = validate_product_payload(payload)
    if errors:
        raise ValidationError(errors)
    return {
        "name": str(payload.get("name", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "hsn_sac": str(payload.get("hsn_sac", "")).strip(),
        "price": round(float(payload.get("price", 0)), 2),
        "gst_rate": round(float(payload.get("gst_rate", 0)), 2),
        "unit": str(payload.get("unit", "")).strip(),
        "active": bool(payload.get("active", True)),
    }


def get_products(search: str = "", active_only: bool = False, current_user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return product/service master records."""
    return list_products(search, active_only, **user_scope(current_user))


def get_product(product_id: int, current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return one product/service by ID."""
    return get_product_by_id(product_id, **user_scope(current_user))


def create_product(payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create a product/service master record."""
    normalized = normalize_product_payload(payload)
    normalized["owner_user_id"] = (current_user or {}).get("id")
    product = insert_product(normalized)
    logger.info("Created product/service %s", product.get("name"))
    return product


def update_product(product_id: int, payload: dict[str, Any], current_user: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Update a product/service master record."""
    current = get_product_by_id(product_id, **user_scope(current_user))
    if current is None:
        return None
    product = update_product_record(product_id, normalize_product_payload({**current, **payload}))
    if product:
        logger.info("Updated product/service %s", product.get("name"))
    return product


def delete_product(product_id: int, current_user: dict[str, Any] | None = None) -> bool:
    """Delete a product/service master record."""
    deleted = delete_product_record(product_id, **user_scope(current_user))
    if deleted:
        logger.info("Deleted product/service id=%s", product_id)
    return deleted

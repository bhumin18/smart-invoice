"""Product and service master API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.product_service import (
    create_product,
    delete_product,
    get_product,
    get_products,
    update_product,
)
from utils.helpers import ValidationError, api_response


product_bp = Blueprint("product_routes", __name__, url_prefix="/api/products")
logger = logging.getLogger(__name__)


@product_bp.get("")
def list_products_route():
    """List product/service master records."""
    try:
        active_only = str(request.args.get("active_only", "")).lower() in {"1", "true", "yes"}
        return api_response(
            True,
            get_products(str(request.args.get("search", "")), active_only, getattr(g, "current_user", {}) or {}),
            "Products fetched successfully",
        )
    except Exception as exc:
        logger.exception("Product listing failed")
        return api_response(False, {}, "Failed to fetch products", 500, {"error": str(exc)})


@product_bp.get("/<int:product_id>")
def get_product_route(product_id: int):
    """Fetch one product/service master record."""
    try:
        product = get_product(product_id, getattr(g, "current_user", {}) or {})
        if product is None:
            return api_response(False, {}, "Product not found", 404)
        return api_response(True, product, "Product fetched successfully")
    except Exception as exc:
        logger.exception("Product fetch failed")
        return api_response(False, {}, "Failed to fetch product", 500, {"error": str(exc)})


@product_bp.post("")
def create_product_route():
    """Create one product/service master record."""
    try:
        return api_response(
            True,
            create_product(request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {}),
            "Product created successfully",
            201,
        )
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Product creation failed")
        return api_response(False, {}, "Failed to create product", 500, {"error": str(exc)})


@product_bp.put("/<int:product_id>")
def update_product_route(product_id: int):
    """Update one product/service master record."""
    try:
        product = update_product(product_id, request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {})
        if product is None:
            return api_response(False, {}, "Product not found", 404)
        return api_response(True, product, "Product updated successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Product update failed")
        return api_response(False, {}, "Failed to update product", 500, {"error": str(exc)})


@product_bp.delete("/<int:product_id>")
def delete_product_route(product_id: int):
    """Delete one product/service master record."""
    try:
        if not delete_product(product_id, getattr(g, "current_user", {}) or {}):
            return api_response(False, {}, "Product not found", 404)
        return api_response(True, {"id": product_id}, "Product deleted successfully")
    except Exception as exc:
        logger.exception("Product delete failed")
        return api_response(False, {}, "Failed to delete product", 500, {"error": str(exc)})

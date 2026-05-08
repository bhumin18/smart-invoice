"""Client master API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.client_service import create_client, delete_client, get_client, get_clients, update_client
from services.import_service import import_clients
from utils.helpers import ValidationError, api_response


client_bp = Blueprint("client_routes", __name__, url_prefix="/api/clients")
logger = logging.getLogger(__name__)


@client_bp.get("")
def list_clients_route():
    """List client master records."""
    try:
        return api_response(
            True,
            get_clients(str(request.args.get("search", "")), getattr(g, "current_user", {}) or {}),
            "Clients fetched successfully",
        )
    except Exception as exc:
        logger.exception("Client listing failed")
        return api_response(False, {}, "Failed to fetch clients", 500, {"error": str(exc)})


@client_bp.get("/<int:client_id>")
def get_client_route(client_id: int):
    """Fetch one client master record."""
    try:
        client = get_client(client_id, getattr(g, "current_user", {}) or {})
        if client is None:
            return api_response(False, {}, "Client not found", 404)
        return api_response(True, client, "Client fetched successfully")
    except Exception as exc:
        logger.exception("Client fetch failed")
        return api_response(False, {}, "Failed to fetch client", 500, {"error": str(exc)})


@client_bp.post("")
def create_client_route():
    """Create one client master record."""
    try:
        return api_response(
            True,
            create_client(request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {}),
            "Client created successfully",
            201,
        )
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Client creation failed")
        return api_response(False, {}, "Failed to create client", 500, {"error": str(exc)})


@client_bp.post("/import")
def import_clients_route():
    """Import client master records from CSV or Excel."""
    try:
        return api_response(
            True,
            import_clients(request.files.get("file"), getattr(g, "current_user", {}) or {}),
            "Clients imported successfully",
        )
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Client import failed")
        return api_response(False, {}, "Failed to import clients", 500, {"error": str(exc)})


@client_bp.put("/<int:client_id>")
def update_client_route(client_id: int):
    """Update one client master record."""
    try:
        client = update_client(client_id, request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {})
        if client is None:
            return api_response(False, {}, "Client not found", 404)
        return api_response(True, client, "Client updated successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Client update failed")
        return api_response(False, {}, "Failed to update client", 500, {"error": str(exc)})


@client_bp.delete("/<int:client_id>")
def delete_client_route(client_id: int):
    """Delete one client master record."""
    try:
        if not delete_client(client_id, getattr(g, "current_user", {}) or {}):
            return api_response(False, {}, "Client not found", 404)
        return api_response(True, {"id": client_id}, "Client deleted successfully")
    except Exception as exc:
        logger.exception("Client delete failed")
        return api_response(False, {}, "Failed to delete client", 500, {"error": str(exc)})

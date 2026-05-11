"""OpenAPI documentation routes."""

from __future__ import annotations

from flask import Blueprint, Response

from utils.helpers import api_response


docs_bp = Blueprint("docs_routes", __name__, url_prefix="/api/docs")


def openapi_spec() -> dict:
    """Return a compact OpenAPI spec for the public API surface."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Smart Invoice + GST Tool API",
            "version": "1.0.0",
            "description": "Flask API for GST invoices, reports, company settings, users, and exports.",
        },
        "servers": [{"url": "/api"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
        "security": [{"bearerAuth": []}],
        "paths": {
            "/health": {"get": {"summary": "Health check"}},
            "/auth/login": {"post": {"summary": "Login"}},
            "/auth/register": {"post": {"summary": "Register account"}},
            "/auth/me": {"get": {"summary": "Current user"}},
            "/invoices": {
                "get": {"summary": "List invoices"},
                "post": {"summary": "Create invoice"},
            },
            "/invoices/{id}": {
                "get": {"summary": "Get invoice"},
                "put": {"summary": "Update invoice"},
                "delete": {"summary": "Delete invoice"},
            },
            "/invoices/{id}/pdf": {"get": {"summary": "Download invoice PDF"}},
            "/invoices/{id}/audit": {"get": {"summary": "Invoice audit history"}},
            "/invoices/{id}/payments": {"post": {"summary": "Record payment"}},
            "/estimates": {
                "get": {"summary": "List estimates"},
                "post": {"summary": "Create estimate"},
            },
            "/estimates/{id}": {
                "get": {"summary": "Get estimate"},
                "put": {"summary": "Update estimate"},
                "delete": {"summary": "Delete estimate"},
            },
            "/estimates/{id}/convert": {"post": {"summary": "Convert estimate to invoice"}},
            "/expenses": {
                "get": {"summary": "List expenses"},
                "post": {"summary": "Create expense"},
            },
            "/expenses/{id}": {
                "get": {"summary": "Get expense"},
                "put": {"summary": "Update expense"},
                "delete": {"summary": "Delete expense"},
            },
            "/clients": {"get": {"summary": "List clients"}, "post": {"summary": "Create client"}},
            "/products": {"get": {"summary": "List products"}, "post": {"summary": "Create product"}},
            "/company": {"get": {"summary": "Get company settings"}, "post": {"summary": "Save company settings"}},
            "/dashboard/summary": {"get": {"summary": "Dashboard summary"}},
            "/dashboard/analytics": {"get": {"summary": "Dashboard chart analytics"}},
            "/reports/gst": {"get": {"summary": "Download GST Excel report"}},
            "/exports/data": {"get": {"summary": "Export data"}},
            "/backups/export": {"get": {"summary": "Download backup zip"}},
        },
    }


@docs_bp.get("")
def docs_index():
    """Return a small HTML documentation entrypoint."""
    html = """
    <!doctype html>
    <html>
      <head><title>Smart Invoice API Docs</title></head>
      <body style="font-family: Arial, sans-serif; max-width: 860px; margin: 40px auto; line-height: 1.5;">
        <h1>Smart Invoice + GST Tool API</h1>
        <p>OpenAPI JSON is available at <a href="/api/docs/openapi.json">/api/docs/openapi.json</a>.</p>
        <p>Use bearer token authentication for protected routes.</p>
      </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@docs_bp.get("/openapi.json")
def docs_openapi():
    """Return the OpenAPI document as JSON."""
    return api_response(True, openapi_spec(), "OpenAPI spec fetched successfully")

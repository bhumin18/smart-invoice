"""Flask entrypoint for Smart Invoice + GST Tool backend API."""

from __future__ import annotations

import logging

from flask import Flask, g, request
from flask_cors import CORS

from branding import DEVELOPER_SIGNATURE, branding_payload, console_banner
from config import APP_DEBUG, CORS_ALLOW_ALL, CORS_ORIGINS, SERVER_HOST, SERVER_PORT, get_public_config
from models.client_model import create_client_table
from models.company_model import create_company_table
from models.invoice_model import create_invoice_tables
from models.product_model import create_product_table
from models.user_model import create_user_table
from routes.auth_routes import auth_bp
from routes.backup_routes import backup_bp
from routes.client_routes import client_bp
from routes.company_routes import company_bp
from routes.dashboard_routes import dashboard_bp
from routes.export_routes import export_bp
from routes.gst_routes import gst_bp
from routes.invoice_routes import invoice_bp
from routes.product_routes import product_bp
from routes.user_routes import user_bp
from services.auth_service import auth_enabled, verify_token
from utils.helpers import api_response, ensure_directories, setup_logging


def init_database() -> None:
    """Initialize database tables and seed required default records."""
    ensure_directories()
    create_user_table()
    create_company_table()
    create_invoice_tables()
    create_client_table()
    create_product_table()


def create_app() -> Flask:
    """Create and configure the Flask application."""
    setup_logging()
    init_database()
    logging.info(console_banner())
    print(console_banner())
    app = Flask(__name__)
    app.config["APP_SIGNATURE"] = DEVELOPER_SIGNATURE
    if CORS_ALLOW_ALL:
        CORS(app)
    else:
        CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})
    app.register_blueprint(auth_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(gst_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(user_bp)

    @app.before_request
    def require_authentication():
        """Protect API routes with bearer auth when enabled."""
        if not auth_enabled():
            return None
        if request.method == "OPTIONS":
            return None
        public_paths = {
            "/api/health",
            "/api/branding",
            "/api/config/public",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/forgot-password",
            "/api/auth/reset-password",
        }
        if request.path in public_paths:
            return None
        if not request.path.startswith("/api/"):
            return None
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        user = verify_token(token) if token else None
        if user is None:
            return api_response(False, {}, "Unauthorized", 401, {"auth": "Valid bearer token is required"})
        g.current_user = user
        return None

    @app.get("/api/health")
    def health_check():
        """Return API health status."""
        return api_response(
            True,
            {"status": "ok", "signature": DEVELOPER_SIGNATURE, "branding": branding_payload()},
            "Backend is running",
        )

    @app.get("/api/branding")
    def app_branding():
        """Return app ownership metadata."""
        return api_response(True, branding_payload(), "Branding fetched successfully")

    @app.get("/api/config/public")
    def public_config():
        """Return safe runtime configuration for diagnostics."""
        return api_response(True, get_public_config(), "Config fetched successfully")

    @app.errorhandler(404)
    def not_found(_error):
        """Return a JSON response for unknown routes."""
        return api_response(False, {}, "Route not found", 404)

    @app.errorhandler(500)
    def server_error(error):
        """Return a JSON response for unexpected server errors."""
        logging.exception("Unhandled server error: %s", error)
        return api_response(False, {}, "Internal server error", 500)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=APP_DEBUG)

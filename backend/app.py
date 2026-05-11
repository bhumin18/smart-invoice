"""Flask entrypoint for Smart Invoice + GST Tool backend API."""

from __future__ import annotations

import logging
import time

from flask import Flask, g, request
from flask_cors import CORS

from branding import DEVELOPER_SIGNATURE, branding_payload, console_banner
from config import APP_DEBUG, CORS_ALLOW_ALL, CORS_ORIGINS, MAX_CONTENT_LENGTH, SERVER_HOST, SERVER_PORT, get_config, get_public_config, validate_runtime_config
from models.audit_model import create_audit_table
from models.client_model import create_client_table
from models.company_model import create_company_table
from models.estimate_model import create_estimate_tables
from models.expense_model import create_expense_table
from models.invoice_model import create_invoice_tables
from models.product_model import create_product_table
from models.recurring_model import create_recurring_table
from models.reminder_model import create_reminder_table
from models.job_model import create_job_table
from models.security_model import create_security_tables
from models.settings_model import create_settings_table
from models.user_model import create_user_table
from routes.auth_routes import auth_bp
from routes.backup_routes import backup_bp
from routes.client_routes import client_bp
from routes.company_routes import company_bp
from routes.dashboard_routes import dashboard_bp
from routes.docs_routes import docs_bp
from routes.export_routes import export_bp
from routes.estimate_routes import estimate_bp
from routes.expense_routes import expense_bp
from routes.gst_routes import gst_bp
from routes.invoice_routes import invoice_bp
from routes.job_routes import job_bp
from routes.product_routes import product_bp
from routes.portal_routes import portal_bp
from routes.recurring_routes import recurring_bp
from routes.reminder_routes import reminder_bp
from routes.user_routes import user_bp
from services.auth_service import auth_enabled, verify_token
from services.scheduler_service import start_scheduler
from utils.helpers import api_response, ensure_directories, setup_logging


def init_database() -> None:
    """Initialize database tables and seed required default records."""
    ensure_directories()
    create_user_table()
    create_company_table()
    create_invoice_tables()
    create_estimate_tables()
    create_expense_table()
    create_client_table()
    create_product_table()
    create_audit_table()
    create_security_tables()
    create_settings_table()
    create_recurring_table()
    create_reminder_table()
    create_job_table()


def create_app() -> Flask:
    """Create and configure the Flask application."""
    setup_logging()
    validate_runtime_config()
    init_database()
    logging.info(console_banner())
    print(console_banner())
    app = Flask(__name__)
    app.config["APP_SIGNATURE"] = DEVELOPER_SIGNATURE
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    if CORS_ALLOW_ALL:
        CORS(app)
    else:
        CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})
    app.register_blueprint(auth_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(estimate_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(job_bp)
    app.register_blueprint(gst_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(reminder_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(user_bp)

    rate_buckets: dict[tuple[str, str], list[float]] = {}

    @app.before_request
    def apply_basic_rate_limits():
        """Apply lightweight per-IP limits to sensitive auth endpoints."""
        if request.path not in {"/api/auth/login", "/api/auth/forgot-password"}:
            return None
        window = int(get_config("security.rate_limit_window_seconds", 60))
        maximum = int(get_config("security.rate_limit_max_requests", 30))
        key = (
            request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip(),
            request.path,
        )
        now = time.time()
        recent = [stamp for stamp in rate_buckets.get(key, []) if now - stamp <= window]
        if len(recent) >= maximum:
            rate_buckets[key] = recent
            return api_response(False, {}, "Too many requests. Please try again later.", 429)
        recent.append(now)
        rate_buckets[key] = recent
        return None

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
            "/api/docs",
            "/api/docs/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/forgot-password",
            "/api/auth/reset-password",
            "/api/auth/verify-email",
        }
        if request.path in public_paths or request.path.startswith("/api/portal/"):
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

    start_scheduler()
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=APP_DEBUG)

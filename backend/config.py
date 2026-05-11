"""Application configuration loaded from YAML with environment overrides."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.getenv("APP_CONFIG_PATH", str(BASE_DIR / "config.yaml")))

DEFAULT_CONFIG: dict[str, Any] = {
    "app": {
        "name": "Smart Invoice + GST Tool",
        "environment": "development",
        "debug": True,
        "secret_key": "change-this-secret-key",
    },
    "server": {"host": "0.0.0.0", "port": 5000},
    "cors": {"allow_all": True, "origins": ["http://localhost:5173"]},
    "database": {
        "engine": "sqlite",
        "sqlite": {"path": "database/db.sqlite3"},
        "postgresql": {"url": "postgresql+psycopg2://user:password@localhost:5432/smart_invoice"},
        "mysql": {"url": "mysql+pymysql://user:password@localhost:3306/smart_invoice"},
        "mongodb": {"uri": "mongodb://localhost:27017/smart_invoice", "database": "smart_invoice"},
    },
    "outputs": {
        "base_dir": "outputs",
        "invoices_dir": "outputs/invoices",
        "reports_dir": "outputs/reports",
        "assets_dir": "outputs/assets",
        "backups_dir": "outputs/backups",
    },
    "email": {
        "enabled": False,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "username": "",
        "password": "",
        "from_email": "",
        "from_name": "Smart Invoice",
    },
    "auth": {
        "enabled": True,
        "allow_registration": True,
        "token_expiry_hours": 24,
        "password_reset_token_minutes": 30,
        "password_reset_url": "http://localhost:5173",
        "admin_username": "admin",
        "admin_password": "admin123",
        "admin_email": "admin@example.com",
    },
    "logging": {"level": "INFO"},
    "security": {
        "max_upload_mb": 10,
        "login_max_attempts": 5,
        "login_lock_minutes": 15,
        "rate_limit_window_seconds": 60,
        "rate_limit_max_requests": 30,
    },
    "scheduler": {
        "enabled": False,
        "timezone": "Asia/Kolkata",
        "daily_hour": 9,
        "daily_minute": 0,
    },
    "portal": {
        "default_link_expiry_days": 30,
    },
    "storage": {
        "provider": "local",
        "s3_endpoint_url": "",
        "s3_bucket": "",
        "s3_access_key_id": "",
        "s3_secret_access_key": "",
        "signed_url_expiry_seconds": 900,
    },
    "tax": {"max_gst_rate": 28, "default_supply_type": "intrastate"},
    "features": {
        "auth_enabled": False,
        "client_master_enabled": True,
        "product_master_enabled": True,
        "dashboard_enabled": True,
        "email_invoice_enabled": True,
        "backup_restore_enabled": True,
    },
}

DEFAULT_SECRET_KEY = "change-this-secret-key"
DEFAULT_ADMIN_PASSWORD = "admin123"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge nested dictionaries while preserving defaults for missing keys."""
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml_config() -> dict[str, Any]:
    """Read YAML config from disk and merge it with defaults."""
    if not CONFIG_PATH.exists():
        return copy.deepcopy(DEFAULT_CONFIG)
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    if not isinstance(loaded, dict):
        raise RuntimeError(f"Invalid config file: {CONFIG_PATH}")
    return _deep_merge(DEFAULT_CONFIG, loaded)


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean value from environment variables."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read an integer value from environment variables."""
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _resolve_backend_path(value: str | Path) -> Path:
    """Resolve relative backend paths against the backend directory."""
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


APP_CONFIG = _load_yaml_config()

# Environment overrides for deployment and secrets.
APP_CONFIG["app"]["environment"] = os.getenv("APP_ENV", APP_CONFIG["app"]["environment"])
APP_CONFIG["app"]["debug"] = _env_bool("APP_DEBUG", bool(APP_CONFIG["app"]["debug"]))
APP_CONFIG["app"]["secret_key"] = os.getenv("SECRET_KEY", str(APP_CONFIG["app"]["secret_key"]))
APP_CONFIG["server"]["host"] = os.getenv("APP_HOST", str(APP_CONFIG["server"]["host"]))
APP_CONFIG["server"]["port"] = _env_int("APP_PORT", int(APP_CONFIG["server"]["port"]))
APP_CONFIG["database"]["engine"] = os.getenv(
    "DATABASE_ENGINE", str(APP_CONFIG["database"]["engine"])
).strip().lower()
APP_CONFIG["database"]["sqlite"]["path"] = os.getenv(
    "SQLITE_DATABASE_PATH", str(APP_CONFIG["database"]["sqlite"]["path"])
)
if os.getenv("DATABASE_URL"):
    engine = APP_CONFIG["database"]["engine"]
    if engine in {"postgresql", "mysql"}:
        APP_CONFIG["database"][engine]["url"] = os.getenv("DATABASE_URL")
if os.getenv("MONGODB_URI"):
    APP_CONFIG["database"]["mongodb"]["uri"] = os.getenv("MONGODB_URI")
APP_CONFIG["logging"]["level"] = os.getenv("LOG_LEVEL", str(APP_CONFIG["logging"]["level"]))
APP_CONFIG["email"]["enabled"] = _env_bool("EMAIL_ENABLED", bool(APP_CONFIG["email"]["enabled"]))
APP_CONFIG["email"]["smtp_host"] = os.getenv("SMTP_HOST", str(APP_CONFIG["email"]["smtp_host"]))
APP_CONFIG["email"]["smtp_port"] = _env_int("SMTP_PORT", int(APP_CONFIG["email"]["smtp_port"]))
APP_CONFIG["email"]["use_tls"] = _env_bool("SMTP_USE_TLS", bool(APP_CONFIG["email"]["use_tls"]))
APP_CONFIG["email"]["username"] = os.getenv("SMTP_USERNAME", str(APP_CONFIG["email"]["username"]))
APP_CONFIG["email"]["password"] = os.getenv("SMTP_PASSWORD", str(APP_CONFIG["email"]["password"]))
APP_CONFIG["email"]["from_email"] = os.getenv("SMTP_FROM_EMAIL", str(APP_CONFIG["email"]["from_email"]))
APP_CONFIG["email"]["from_name"] = os.getenv("SMTP_FROM_NAME", str(APP_CONFIG["email"]["from_name"]))
APP_CONFIG["security"]["max_upload_mb"] = _env_int("MAX_UPLOAD_MB", int(APP_CONFIG["security"]["max_upload_mb"]))
APP_CONFIG["security"]["login_max_attempts"] = _env_int(
    "LOGIN_MAX_ATTEMPTS", int(APP_CONFIG["security"]["login_max_attempts"])
)
APP_CONFIG["security"]["login_lock_minutes"] = _env_int(
    "LOGIN_LOCK_MINUTES", int(APP_CONFIG["security"]["login_lock_minutes"])
)
APP_CONFIG["security"]["rate_limit_window_seconds"] = _env_int(
    "RATE_LIMIT_WINDOW_SECONDS", int(APP_CONFIG["security"]["rate_limit_window_seconds"])
)
APP_CONFIG["security"]["rate_limit_max_requests"] = _env_int(
    "RATE_LIMIT_MAX_REQUESTS", int(APP_CONFIG["security"]["rate_limit_max_requests"])
)
APP_CONFIG["scheduler"]["enabled"] = _env_bool("SCHEDULER_ENABLED", bool(APP_CONFIG["scheduler"]["enabled"]))
APP_CONFIG["scheduler"]["daily_hour"] = _env_int("SCHEDULER_DAILY_HOUR", int(APP_CONFIG["scheduler"]["daily_hour"]))
APP_CONFIG["scheduler"]["daily_minute"] = _env_int(
    "SCHEDULER_DAILY_MINUTE", int(APP_CONFIG["scheduler"]["daily_minute"])
)
APP_CONFIG["auth"]["enabled"] = _env_bool("AUTH_ENABLED", bool(APP_CONFIG["auth"]["enabled"]))
APP_CONFIG["auth"]["allow_registration"] = _env_bool(
    "AUTH_ALLOW_REGISTRATION", bool(APP_CONFIG["auth"]["allow_registration"])
)
APP_CONFIG["auth"]["token_expiry_hours"] = _env_int(
    "AUTH_TOKEN_EXPIRY_HOURS", int(APP_CONFIG["auth"]["token_expiry_hours"])
)
APP_CONFIG["auth"]["password_reset_token_minutes"] = _env_int(
    "AUTH_PASSWORD_RESET_TOKEN_MINUTES", int(APP_CONFIG["auth"]["password_reset_token_minutes"])
)
APP_CONFIG["auth"]["password_reset_url"] = os.getenv(
    "AUTH_PASSWORD_RESET_URL", str(APP_CONFIG["auth"]["password_reset_url"])
)
APP_CONFIG["auth"]["admin_username"] = os.getenv(
    "ADMIN_USERNAME", str(APP_CONFIG["auth"]["admin_username"])
)
APP_CONFIG["auth"]["admin_password"] = os.getenv(
    "ADMIN_PASSWORD", str(APP_CONFIG["auth"]["admin_password"])
)
APP_CONFIG["auth"]["admin_email"] = os.getenv(
    "ADMIN_EMAIL", str(APP_CONFIG["auth"]["admin_email"])
)


def get_config(path: str | None = None, default: Any = None) -> Any:
    """Return a config value by dotted path, or the whole config if omitted."""
    if path is None:
        return copy.deepcopy(APP_CONFIG)
    current: Any = APP_CONFIG
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def get_public_config() -> dict[str, Any]:
    """Return non-secret configuration safe for frontend diagnostics."""
    return {
        "app": {
            "name": get_config("app.name"),
            "environment": get_config("app.environment"),
            "debug": get_config("app.debug"),
        },
        "server": {
            "host": get_config("server.host"),
            "port": get_config("server.port"),
        },
        "database": {
            "engine": DATABASE_ENGINE,
            "active_adapter": "sqlite3" if DATABASE_ENGINE == "sqlite" else "not_enabled",
            "available_adapter": "sqlite",
            "future_config_profiles": ["postgresql", "mysql", "mongodb"],
        },
        "features": get_config("features", {}),
        "auth": {"enabled": bool(get_config("auth.enabled", True))},
        "tax": get_config("tax", {}),
        "email": {
            "enabled": bool(get_config("email.enabled", False)),
            "smtp_host": get_config("email.smtp_host", ""),
            "smtp_port": get_config("email.smtp_port", 587),
            "from_email_configured": bool(get_config("email.from_email", "")),
        },
    }


DATABASE_ENGINE = str(get_config("database.engine", "sqlite")).strip().lower()
SQLITE_DATABASE_PATH = _resolve_backend_path(get_config("database.sqlite.path", "database/db.sqlite3"))
DATABASE_URL = str(
    get_config(f"database.{DATABASE_ENGINE}.url", f"sqlite:///{SQLITE_DATABASE_PATH}")
    if DATABASE_ENGINE != "mongodb"
    else get_config("database.mongodb.uri", "")
)
SERVER_HOST = str(get_config("server.host", "0.0.0.0"))
SERVER_PORT = int(get_config("server.port", 5000))
APP_DEBUG = bool(get_config("app.debug", True))
SECRET_KEY = str(get_config("app.secret_key", "change-this-secret-key"))
CORS_ALLOW_ALL = bool(get_config("cors.allow_all", True))
CORS_ORIGINS = list(get_config("cors.origins", []) or [])
LOG_LEVEL = str(get_config("logging.level", "INFO")).upper()
MAX_GST_RATE = float(get_config("tax.max_gst_rate", 28))
DEFAULT_SUPPLY_TYPE = str(get_config("tax.default_supply_type", "intrastate")).lower()
OUTPUT_BASE_DIR = _resolve_backend_path(get_config("outputs.base_dir", "outputs"))
INVOICE_OUTPUT_PATH = _resolve_backend_path(get_config("outputs.invoices_dir", "outputs/invoices"))
REPORT_OUTPUT_PATH = _resolve_backend_path(get_config("outputs.reports_dir", "outputs/reports"))
ASSETS_OUTPUT_PATH = _resolve_backend_path(get_config("outputs.assets_dir", "outputs/assets"))
BACKUPS_OUTPUT_PATH = _resolve_backend_path(get_config("outputs.backups_dir", "outputs/backups"))
MAX_CONTENT_LENGTH = int(get_config("security.max_upload_mb", 10)) * 1024 * 1024


def validate_database_config() -> None:
    """Validate database settings supported by the active model adapter."""
    if DATABASE_ENGINE != "sqlite":
        raise RuntimeError(
            f"DATABASE_ENGINE={DATABASE_ENGINE!r} is configured in {CONFIG_PATH.name}, "
            "but the active backend model adapter is sqlite3. Keep engine: sqlite for "
            "the current app, or add a SQLAlchemy/MongoDB repository adapter before "
            "activating PostgreSQL, MySQL, or MongoDB."
        )


def validate_runtime_config() -> None:
    """Fail fast when unsafe development defaults are used in production."""
    environment = str(get_config("app.environment", "development")).strip().lower()
    if environment != "production":
        return

    errors: list[str] = []
    if SECRET_KEY == DEFAULT_SECRET_KEY:
        errors.append("SECRET_KEY/app.secret_key must be changed in production")
    if bool(get_config("auth.enabled", True)) and str(get_config("auth.admin_password", "")) == DEFAULT_ADMIN_PASSWORD:
        errors.append("ADMIN_PASSWORD/auth.admin_password must be changed in production")
    if bool(get_config("cors.allow_all", False)):
        errors.append("cors.allow_all must be false in production")
    if APP_DEBUG:
        errors.append("APP_DEBUG/app.debug must be false in production")

    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))

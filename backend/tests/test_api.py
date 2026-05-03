"""Backend API regression tests."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
import yaml


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    """Create a Flask test client with an isolated SQLite database."""
    tmp_path = tmp_path_factory.mktemp("smart_invoice_backend")
    config = {
        "app": {
            "environment": "testing",
            "debug": False,
            "secret_key": "test-secret-key",
        },
        "server": {"host": "127.0.0.1", "port": 5000},
        "cors": {"allow_all": True},
        "database": {"engine": "sqlite", "sqlite": {"path": str(tmp_path / "db.sqlite3")}},
        "outputs": {
            "base_dir": str(tmp_path / "outputs"),
            "invoices_dir": str(tmp_path / "outputs" / "invoices"),
            "reports_dir": str(tmp_path / "outputs" / "reports"),
            "assets_dir": str(tmp_path / "outputs" / "assets"),
            "backups_dir": str(tmp_path / "outputs" / "backups"),
        },
        "email": {"enabled": False},
        "auth": {
            "enabled": True,
            "allow_registration": True,
            "token_expiry_hours": 24,
            "admin_username": "admin",
            "admin_password": "admin123",
            "admin_email": "admin@example.com",
        },
        "tax": {"max_gst_rate": 28, "default_supply_type": "intrastate"},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    os.environ["APP_CONFIG_PATH"] = str(config_path)

    app_module = importlib.import_module("app")
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


def _login(client, username: str = "admin", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def _invoice_payload(invoice_number: str = "") -> dict:
    return {
        "invoice_number": invoice_number,
        "client_name": "Acme Services",
        "client_gstin": "24ABCDE1234F1Z8",
        "client_address": "Ahmedabad, Gujarat",
        "date": "2026-05-03",
        "due_date": "2026-05-18",
        "supply_type": "intrastate",
        "items": [
            {"item_name": "Consulting", "quantity": 2, "price": 1000, "gst_rate": 18},
            {"item_name": "Hosting", "quantity": 1, "price": 500, "gst_rate": 5},
        ],
    }


def test_invoice_crud_pdf_and_audit(client):
    """Create, update, download PDF, record payment, void, audit, and delete an invoice."""
    headers = _login(client)
    created = client.post("/api/invoices", json=_invoice_payload(), headers=headers)
    assert created.status_code == 201
    invoice = created.get_json()["data"]
    assert invoice["subtotal"] == 2500.0
    assert invoice["gst_amount"] == 385.0
    assert invoice["total"] == 2885.0

    invoice_id = invoice["id"]
    pdf = client.get(f"/api/invoices/{invoice_id}/pdf", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["Content-Type"].startswith("application/pdf")

    payload = _invoice_payload(invoice["invoice_number"])
    payload["client_name"] = "Acme Services Updated"
    updated = client.put(f"/api/invoices/{invoice_id}", json=payload, headers=headers)
    assert updated.status_code == 200
    assert updated.get_json()["data"]["client_name"] == "Acme Services Updated"

    payment = client.post(
        f"/api/invoices/{invoice_id}/payments",
        json={"amount": 1000, "date": "2026-05-04", "mode": "UPI"},
        headers=headers,
    )
    assert payment.status_code == 201
    assert payment.get_json()["data"]["status"] == "partially paid"

    voided = client.post(f"/api/invoices/{invoice_id}/void", json={"reason": "test void"}, headers=headers)
    assert voided.status_code == 200
    assert voided.get_json()["data"]["status"] == "void"

    audit = client.get(f"/api/invoices/{invoice_id}/audit", headers=headers)
    assert audit.status_code == 200
    actions = {row["action"] for row in audit.get_json()["data"]}
    assert {"created", "updated", "payment_recorded", "voided"}.issubset(actions)

    deleted = client.delete(f"/api/invoices/{invoice_id}", headers=headers)
    assert deleted.status_code == 200


def test_validation_errors(client):
    """Reject empty invoices and invalid GST values."""
    headers = _login(client)
    response = client.post(
        "/api/invoices",
        json={"client_name": "", "items": [{"item_name": "", "quantity": 0, "price": -1, "gst_rate": 40}]},
        headers=headers,
    )
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert "client_name" in errors
    assert "items[0].quantity" in errors
    assert "items[0].gst_rate" in errors


def test_user_scoping_allows_same_invoice_number_per_user(client):
    """Allow separate users to use the same invoice number while hiding each other's data."""
    admin_headers = _login(client)
    admin_invoice = client.post(
        "/api/invoices",
        json=_invoice_payload("INV-SAME"),
        headers=admin_headers,
    )
    assert admin_invoice.status_code == 201

    registered = client.post(
        "/api/auth/register",
        json={"username": "demo-user", "email": "demo@example.com", "password": "secret123"},
    )
    assert registered.status_code == 201
    user_headers = _login(client, "demo-user", "secret123")
    user_invoice = client.post(
        "/api/invoices",
        json=_invoice_payload("INV-SAME"),
        headers=user_headers,
    )
    assert user_invoice.status_code == 201

    listed = client.get("/api/invoices", headers=user_headers)
    assert listed.status_code == 200
    invoices = listed.get_json()["data"]
    assert len(invoices) == 1
    assert invoices[0]["owner_user_id"] == registered.get_json()["data"]["id"]


def test_gst_breakdown_split():
    """Split GST into CGST/SGST for intrastate and IGST for interstate."""
    from utils.helpers import calculate_item_totals, get_gst_breakdown

    items = [calculate_item_totals({"item_name": "Service", "quantity": 1, "price": 1000, "gst_rate": 18})]
    intra = get_gst_breakdown(items, "intrastate")[0]
    inter = get_gst_breakdown(items, "interstate")[0]
    assert intra["cgst"] == 90.0
    assert intra["sgst"] == 90.0
    assert intra["igst"] == 0.0
    assert inter["cgst"] == 0.0
    assert inter["sgst"] == 0.0
    assert inter["igst"] == 180.0

"""Seed realistic demo data for local portfolio testing.

Run from the repository root:
    python backend/scripts/seed_demo.py

Use --reset to delete the configured SQLite database before seeding:
    python backend/scripts/seed_demo.py --reset
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import SQLITE_DATABASE_PATH  # noqa: E402
from config import get_config  # noqa: E402
from models.audit_model import create_audit_table  # noqa: E402
from models.client_model import create_client_table  # noqa: E402
from models.company_model import create_company_table, update_company  # noqa: E402
from models.estimate_model import create_estimate_tables  # noqa: E402
from models.expense_model import create_expense_table  # noqa: E402
from models.invoice_model import create_invoice_tables  # noqa: E402
from models.job_model import create_job_table  # noqa: E402
from models.product_model import create_product_table  # noqa: E402
from models.recurring_model import create_recurring_table  # noqa: E402
from models.reminder_model import create_reminder_table  # noqa: E402
from models.security_model import create_security_tables  # noqa: E402
from models.settings_model import create_settings_table  # noqa: E402
from models.user_model import create_user_table, get_user_by_username  # noqa: E402
from services.client_service import create_client, get_clients  # noqa: E402
from services.estimate_service import create_estimate  # noqa: E402
from services.expense_service import create_expense  # noqa: E402
from services.invoice_service import create_invoice  # noqa: E402
from services.pdf_service import generate_invoice_pdf  # noqa: E402
from services.product_service import create_product, get_products  # noqa: E402
from services.recurring_service import create_recurring_profile  # noqa: E402
from utils.helpers import ensure_directories  # noqa: E402


def init_database() -> None:
    """Create the same tables used by the Flask app."""
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


def current_admin() -> dict[str, Any]:
    """Return the seeded admin user for demo ownership."""
    user = get_user_by_username(str(get_config("auth.admin_username", "admin")))
    if not user:
        raise RuntimeError("Admin user was not created. Check auth.admin_username in config.yaml.")
    return {
        "id": user["id"],
        "username": user["username"],
        "role": "admin",
        "can_create_invoices": True,
        "can_manage_company": True,
        "can_export_data": True,
    }


def find_by_name(rows: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """Find a demo row by case-insensitive name."""
    target = name.strip().lower()
    return next((row for row in rows if str(row.get("name", "")).strip().lower() == target), None)


def seed_company(user: dict[str, Any]) -> None:
    """Create a polished demo company profile."""
    update_company(
        {
            "name": "GemCraft Studio",
            "legal_name": "GemCraft Studio Private Limited",
            "gstin": "24ABCDE1234F1Z5",
            "pan": "ABCDE1234F",
            "address": "402, Sapphire Business Hub, Surat, Gujarat 395007",
            "state": "Gujarat",
            "phone": "+91 98765 43210",
            "email": "accounts@gemcraft.example",
            "website": "https://gemcraft.example",
            "bank_name": "HDFC Bank",
            "bank_account_name": "GemCraft Studio Private Limited",
            "bank_account_number": "50100234567890",
            "bank_ifsc": "HDFC0001234",
            "upi_id": "gemcraft@upi",
            "invoice_prefix": "INV",
            "current_number": 0,
            "invoice_number_padding": 4,
            "currency_symbol": "Rs.",
            "default_payment_terms": "Due within 15 days",
            "terms_and_conditions": "Payment is due as per agreed terms. Goods and services once delivered are non-refundable.",
            "authorized_signatory_name": "Bhumin Paladiya",
            "pdf_template": "simple",
        },
        owner_user_id=int(user["id"]),
    )


def seed_clients(user: dict[str, Any]) -> list[dict[str, Any]]:
    """Create demo clients if they do not already exist."""
    client_payloads = [
        {
            "name": "Aarav Exports",
            "gstin": "27AAECA1234F1Z2",
            "address": "Andheri East, Mumbai, Maharashtra",
            "state": "Maharashtra",
            "phone": "+91 91234 56780",
            "email": "finance@aaravexports.example",
        },
        {
            "name": "Surat Diamond Works",
            "gstin": "24AABCS9876K1Z1",
            "address": "Varachha Road, Surat, Gujarat",
            "state": "Gujarat",
            "phone": "+91 99887 77665",
            "email": "billing@suratdiamond.example",
        },
    ]
    existing = get_clients(current_user=user)
    clients = []
    for payload in client_payloads:
        found = find_by_name(existing, payload["name"])
        clients.append(found or create_client(payload, current_user=user))
    return clients


def seed_products(user: dict[str, Any]) -> list[dict[str, Any]]:
    """Create demo products and services."""
    product_payloads = [
        {"name": "Invoice Management Setup", "description": "One-time setup and training", "hsn_sac": "998314", "price": 15000, "gst_rate": 18, "unit": "service"},
        {"name": "Monthly Accounting Support", "description": "Monthly bookkeeping and GST support", "hsn_sac": "998222", "price": 8500, "gst_rate": 18, "unit": "month"},
        {"name": "Website Maintenance", "description": "Small business website updates", "hsn_sac": "998313", "price": 12000, "gst_rate": 18, "unit": "service"},
    ]
    existing = get_products(current_user=user)
    products = []
    for payload in product_payloads:
        found = find_by_name(existing, payload["name"])
        products.append(found or create_product(payload, current_user=user))
    return products


def seed_invoices(user: dict[str, Any], clients: list[dict[str, Any]], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create sample invoices and generate their PDFs."""
    today = date.today()
    invoices = []
    samples = [
        {
            "client": clients[0],
            "date": (today - timedelta(days=9)).isoformat(),
            "due_date": (today + timedelta(days=6)).isoformat(),
            "supply_type": "interstate",
            "status": "sent",
            "items": [
                {"item_name": products[0]["name"], "description": products[0]["description"], "hsn_sac": products[0]["hsn_sac"], "quantity": 1, "price": products[0]["price"], "gst_rate": products[0]["gst_rate"]},
                {"item_name": products[2]["name"], "description": products[2]["description"], "hsn_sac": products[2]["hsn_sac"], "quantity": 1, "price": products[2]["price"], "gst_rate": products[2]["gst_rate"]},
            ],
        },
        {
            "client": clients[1],
            "date": today.isoformat(),
            "due_date": (today + timedelta(days=15)).isoformat(),
            "supply_type": "intrastate",
            "status": "draft",
            "items": [
                {"item_name": products[1]["name"], "description": products[1]["description"], "hsn_sac": products[1]["hsn_sac"], "quantity": 2, "price": products[1]["price"], "gst_rate": products[1]["gst_rate"]},
            ],
        },
    ]
    for sample in samples:
        client = sample.pop("client")
        invoice = create_invoice(
            {
                "client_name": client["name"],
                "client_gstin": client.get("gstin", ""),
                "client_address": client.get("address", ""),
                "place_of_supply": client.get("state", ""),
                "payment_terms": "Due within 15 days",
                "notes": "Seed demo invoice for portfolio testing.",
                **sample,
            },
            current_user=user,
        )
        generate_invoice_pdf(invoice)
        invoices.append(invoice)
    return invoices


def seed_recurring(user: dict[str, Any], client: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    """Create a recurring invoice profile."""
    return create_recurring_profile(
        {
            "name": "Monthly GST Support Retainer",
            "frequency": "monthly",
            "next_run_date": (date.today() + timedelta(days=20)).isoformat(),
            "active": True,
            "invoice": {
                "client_name": client["name"],
                "client_gstin": client.get("gstin", ""),
                "client_address": client.get("address", ""),
                "date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=15)).isoformat(),
                "supply_type": "intrastate",
                "place_of_supply": client.get("state", ""),
                "status": "draft",
                "payment_terms": "Due within 15 days",
                "items": [
                    {
                        "item_name": product["name"],
                        "description": product.get("description", ""),
                        "hsn_sac": product.get("hsn_sac", ""),
                        "quantity": 1,
                        "price": product["price"],
                        "gst_rate": product["gst_rate"],
                    }
                ],
            },
        },
        current_user=user,
    )


def seed_estimate(user: dict[str, Any], client: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    """Create a demo estimate."""
    return create_estimate(
        {
            "client_name": client["name"],
            "client_gstin": client.get("gstin", ""),
            "client_address": client.get("address", ""),
            "date": date.today().isoformat(),
            "valid_until": (date.today() + timedelta(days=30)).isoformat(),
            "supply_type": "interstate",
            "place_of_supply": client.get("state", ""),
            "status": "sent",
            "notes": "Demo quotation ready to convert into an invoice.",
            "items": [
                {
                    "item_name": product["name"],
                    "description": product.get("description", ""),
                    "hsn_sac": product.get("hsn_sac", ""),
                    "quantity": 1,
                    "price": product["price"],
                    "gst_rate": product["gst_rate"],
                }
            ],
        },
        current_user=user,
    )


def seed_expenses(user: dict[str, Any]) -> list[dict[str, Any]]:
    """Create demo expenses for GST input credit examples."""
    samples = [
        {
            "vendor_name": "Cloud Hosting India",
            "gstin": "29AACCC1111R1Z9",
            "category": "Software",
            "expense_date": (date.today() - timedelta(days=12)).isoformat(),
            "taxable_amount": 4200,
            "gst_rate": 18,
            "payment_mode": "Card",
            "notes": "Monthly hosting expense",
        },
        {
            "vendor_name": "Office Supplies Surat",
            "gstin": "24AAACO2222B1Z3",
            "category": "Office",
            "expense_date": (date.today() - timedelta(days=4)).isoformat(),
            "taxable_amount": 1800,
            "gst_rate": 18,
            "payment_mode": "UPI",
            "notes": "Stationery and printing",
        },
    ]
    return [create_expense(sample, current_user=user) for sample in samples]


def main() -> None:
    """Seed demo data."""
    parser = argparse.ArgumentParser(description="Seed Smart Invoice demo data")
    parser.add_argument("--reset", action="store_true", help="Delete the configured SQLite database before seeding")
    args = parser.parse_args()

    if args.reset and SQLITE_DATABASE_PATH.exists():
        SQLITE_DATABASE_PATH.unlink()
        print(f"Deleted {SQLITE_DATABASE_PATH}")

    init_database()
    user = current_admin()
    seed_company(user)
    clients = seed_clients(user)
    products = seed_products(user)
    invoices = seed_invoices(user, clients, products)
    recurring = seed_recurring(user, clients[1], products[1])
    estimate = seed_estimate(user, clients[0], products[2])
    expenses = seed_expenses(user)

    print("Demo data ready.")
    print(f"Admin user: {user['username']}")
    print(f"Clients: {len(clients)}")
    print(f"Products: {len(products)}")
    print(f"Invoices created: {len(invoices)}")
    print(f"Recurring profile id: {recurring.get('id')}")
    print(f"Estimate created: {estimate.get('estimate_number')}")
    print(f"Expenses created: {len(expenses)}")


if __name__ == "__main__":
    main()

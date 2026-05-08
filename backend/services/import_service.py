"""CSV/Excel import helpers for clients and products."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from services.client_service import create_client
from services.product_service import create_product
from utils.helpers import ValidationError


def _read_upload(file_storage) -> pd.DataFrame:
    """Read a CSV/XLSX upload into a dataframe."""
    if file_storage is None or not file_storage.filename:
        raise ValidationError({"file": "CSV or Excel file is required"})
    name = file_storage.filename.lower()
    content = file_storage.read()
    if name.endswith(".csv"):
        return pd.read_csv(BytesIO(content))
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(content))
    raise ValidationError({"file": "Upload must be .csv, .xlsx, or .xls"})


def _clean(value: Any) -> str:
    """Return a clean string value from spreadsheet data."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def import_clients(file_storage, current_user: dict[str, Any]) -> dict[str, Any]:
    """Import clients from CSV or Excel."""
    df = _read_upload(file_storage)
    created = []
    errors: list[dict[str, Any]] = []
    for index, row in df.iterrows():
        payload = {
            "name": _clean(row.get("name") or row.get("client_name")),
            "gstin": _clean(row.get("gstin") or row.get("client_gstin")),
            "address": _clean(row.get("address")),
            "state": _clean(row.get("state")),
            "phone": _clean(row.get("phone")),
            "email": _clean(row.get("email")),
            "notes": _clean(row.get("notes")),
        }
        try:
            created.append(create_client(payload, current_user))
        except Exception as exc:
            errors.append({"row": int(index) + 2, "message": str(exc)})
    return {"created_count": len(created), "error_count": len(errors), "errors": errors[:25]}


def import_products(file_storage, current_user: dict[str, Any]) -> dict[str, Any]:
    """Import products/services from CSV or Excel."""
    df = _read_upload(file_storage)
    created = []
    errors: list[dict[str, Any]] = []
    for index, row in df.iterrows():
        payload = {
            "name": _clean(row.get("name") or row.get("item_name")),
            "description": _clean(row.get("description")),
            "hsn_sac": _clean(row.get("hsn_sac") or row.get("hsn")),
            "price": float(row.get("price") or 0),
            "gst_rate": float(row.get("gst_rate") or row.get("gst") or 18),
            "unit": _clean(row.get("unit")),
            "active": True,
        }
        try:
            created.append(create_product(payload, current_user))
        except Exception as exc:
            errors.append({"row": int(index) + 2, "message": str(exc)})
    return {"created_count": len(created), "error_count": len(errors), "errors": errors[:25]}

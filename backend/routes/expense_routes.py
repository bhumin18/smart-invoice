"""Expense tracking API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g, request

from services.expense_service import create_expense, delete_expense, get_expense, get_expenses, update_expense
from utils.helpers import ValidationError, api_response


expense_bp = Blueprint("expense_routes", __name__, url_prefix="/api/expenses")
logger = logging.getLogger(__name__)


@expense_bp.get("")
def list_expenses_route():
    """List expenses."""
    try:
        return api_response(True, get_expenses(getattr(g, "current_user", {}) or {}), "Expenses fetched successfully")
    except Exception as exc:
        logger.exception("Expense listing failed")
        return api_response(False, {}, "Failed to fetch expenses", 500, {"error": str(exc)})


@expense_bp.post("")
def create_expense_route():
    """Create an expense."""
    try:
        return api_response(
            True,
            create_expense(request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {}),
            "Expense created successfully",
            201,
        )
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Expense creation failed")
        return api_response(False, {}, "Failed to create expense", 500, {"error": str(exc)})


@expense_bp.get("/<int:expense_id>")
def get_expense_route(expense_id: int):
    """Fetch one expense."""
    try:
        expense = get_expense(expense_id, getattr(g, "current_user", {}) or {})
        if expense is None:
            return api_response(False, {}, "Expense not found", 404)
        return api_response(True, expense, "Expense fetched successfully")
    except Exception as exc:
        logger.exception("Expense fetch failed")
        return api_response(False, {}, "Failed to fetch expense", 500, {"error": str(exc)})


@expense_bp.put("/<int:expense_id>")
def update_expense_route(expense_id: int):
    """Update one expense."""
    try:
        expense = update_expense(expense_id, request.get_json(silent=True) or {}, getattr(g, "current_user", {}) or {})
        if expense is None:
            return api_response(False, {}, "Expense not found", 404)
        return api_response(True, expense, "Expense updated successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 400, exc.errors)
    except Exception as exc:
        logger.exception("Expense update failed")
        return api_response(False, {}, "Failed to update expense", 500, {"error": str(exc)})


@expense_bp.delete("/<int:expense_id>")
def delete_expense_route(expense_id: int):
    """Delete one expense."""
    try:
        if not delete_expense(expense_id, getattr(g, "current_user", {}) or {}):
            return api_response(False, {}, "Expense not found", 404)
        return api_response(True, {"id": expense_id}, "Expense deleted successfully")
    except Exception as exc:
        logger.exception("Expense delete failed")
        return api_response(False, {}, "Failed to delete expense", 500, {"error": str(exc)})


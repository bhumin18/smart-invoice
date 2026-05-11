"""Background scheduler service for recurring invoices and reminders."""

from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from config import get_config
from models.job_model import insert_job_log, list_job_logs
from models.user_model import list_users
from services.auth_service import require_admin
from services.recurring_service import run_due_recurring
from services.reminder_service import run_auto_reminders

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _job_user(user: dict[str, Any]) -> dict[str, Any]:
    """Return a minimal current_user payload for scheduled jobs."""
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "role": user.get("role", "user"),
        "active": bool(user.get("active", True)),
        "can_create_invoices": bool(user.get("can_create_invoices", True)),
        "can_manage_company": bool(user.get("can_manage_company", True)),
        "can_export_data": bool(user.get("can_export_data", True)),
    }


def run_scheduled_jobs() -> dict[str, Any]:
    """Run recurring invoice and payment reminder jobs for all active users."""
    generated_total = 0
    reminder_sent_total = 0
    errors: list[dict[str, Any]] = []
    for user in list_users():
        if not bool(user.get("active", True)):
            continue
        current_user = _job_user(user)
        try:
            recurring = run_due_recurring(current_user)
            reminders = run_auto_reminders(current_user)
            generated_total += int(recurring.get("generated_count", 0))
            reminder_sent_total += int(reminders.get("sent_count", 0))
        except Exception as exc:
            logger.exception("Scheduled job failed for user id=%s", user.get("id"))
            errors.append({"user_id": user.get("id"), "message": str(exc)})
    status = "success" if not errors else "partial"
    result = {
        "generated_invoices": generated_total,
        "sent_reminders": reminder_sent_total,
        "error_count": len(errors),
        "errors": errors[:25],
    }
    insert_job_log("daily_recurring_and_reminders", status, "Scheduled jobs processed", result)
    return result


def run_jobs_now(current_user: dict[str, Any]) -> dict[str, Any]:
    """Run scheduled jobs manually from the admin panel."""
    require_admin(current_user)
    return run_scheduled_jobs()


def get_scheduler_status(current_user: dict[str, Any]) -> dict[str, Any]:
    """Return scheduler settings and recent job logs."""
    require_admin(current_user)
    return {
        "enabled": bool(get_config("scheduler.enabled", False)),
        "daily_hour": int(get_config("scheduler.daily_hour", 9)),
        "daily_minute": int(get_config("scheduler.daily_minute", 0)),
        "logs": list_job_logs(50),
    }


def start_scheduler() -> None:
    """Start APScheduler when enabled by config."""
    global _scheduler
    if _scheduler is not None or not bool(get_config("scheduler.enabled", False)):
        return
    scheduler = BackgroundScheduler(timezone=str(get_config("scheduler.timezone", "Asia/Kolkata")))
    scheduler.add_job(
        run_scheduled_jobs,
        "cron",
        hour=int(get_config("scheduler.daily_hour", 9)),
        minute=int(get_config("scheduler.daily_minute", 0)),
        id="daily_recurring_and_reminders",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Background scheduler started")

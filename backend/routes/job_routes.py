"""Background job and scheduler API routes."""

from __future__ import annotations

import logging

from flask import Blueprint, g

from services.scheduler_service import get_scheduler_status, run_jobs_now
from utils.helpers import ValidationError, api_response


job_bp = Blueprint("job_routes", __name__, url_prefix="/api/jobs")
logger = logging.getLogger(__name__)


@job_bp.get("")
def scheduler_status_route():
    """Return scheduler status and job logs."""
    try:
        return api_response(True, get_scheduler_status(getattr(g, "current_user", {}) or {}), "Scheduler status fetched successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except Exception as exc:
        logger.exception("Scheduler status fetch failed")
        return api_response(False, {}, "Failed to fetch scheduler status", 500, {"error": str(exc)})


@job_bp.post("/run")
def run_jobs_route():
    """Manually run scheduled jobs."""
    try:
        return api_response(True, run_jobs_now(getattr(g, "current_user", {}) or {}), "Scheduled jobs processed successfully")
    except ValidationError as exc:
        return api_response(False, {}, exc.message, 403, exc.errors)
    except Exception as exc:
        logger.exception("Manual scheduled job run failed")
        return api_response(False, {}, "Failed to run scheduled jobs", 500, {"error": str(exc)})

"""Dashboard API routes for IAM compliance posture visibility."""

from __future__ import annotations

from flask import Blueprint
from flask_cors import cross_origin

from ..engine.api_service import get_dashboard_summary
from .utils import error_response, success_response


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.get("/summary")
@cross_origin()
def get_summary():
    """Return a consolidated IAM dashboard summary for executive and audit views."""

    try:
        summary = get_dashboard_summary()
        return success_response(summary)
    except Exception:
        return error_response("Unable to fetch dashboard summary.", 500, 500)

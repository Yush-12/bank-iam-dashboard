"""Request middleware and health endpoint for IAM API operational readiness."""

from __future__ import annotations

import time

from flask import Blueprint, Flask, g, request
from flask_cors import cross_origin

from .engine.api_service import get_db_health
from .routes.utils import error_response, success_response


health_bp = Blueprint("health", __name__, url_prefix="/api")


def register_request_middleware(app: Flask) -> None:
    """Register request timing middleware for structured latency and status logging."""

    @app.before_request
    def _start_timer():
        """Capture request start time for response latency calculation."""

        g.request_started_at = time.perf_counter()

    @app.after_request
    def _log_request(response):
        """Log method, path, status, and processing duration in milliseconds."""

        started_at = getattr(g, "request_started_at", None)
        elapsed_ms = int((time.perf_counter() - started_at) * 1000) if started_at else 0
        app.logger.info(
            "[%s] %s -> %s in %sms",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response


@health_bp.get("/health")
@cross_origin()
def health_check():
    """Return service and database health status for liveness/readiness probing."""

    try:
        data = get_db_health()
        return success_response(data)
    except Exception:
        return error_response("Service health check failed.", 500, 500)

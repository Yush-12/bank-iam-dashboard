"""Violation management API routes for SoD, orphan, and over-privilege findings."""

from __future__ import annotations

from flask import Blueprint, request
from flask_cors import cross_origin

from ..engine.api_service import (
    get_orphan_accounts,
    get_over_privileged_users,
    get_sod_violations,
    update_violation_status,
)
from .utils import error_response, parse_pagination, success_response


violations_bp = Blueprint("violations", __name__, url_prefix="/api/violations")


@violations_bp.get("/sod")
@cross_origin()
def list_sod_violations():
    """Return paginated SoD violation results with optional severity and status filters."""

    try:
        severity = request.args.get("severity")
        status = request.args.get("status")
        limit, offset = parse_pagination()
        results = get_sod_violations(
            severity=severity,
            status=status,
            limit=limit,
            offset=offset,
        )
        return success_response(results)
    except Exception:
        return error_response("Unable to fetch SoD violations.", 500, 500)


@violations_bp.get("/orphans")
@cross_origin()
def list_orphan_accounts():
    """Return paginated orphan-account findings for inactive employees with active access."""

    try:
        limit, offset = parse_pagination()
        results = get_orphan_accounts(limit=limit, offset=offset)
        return success_response(results)
    except Exception:
        return error_response("Unable to fetch orphan accounts.", 500, 500)


@violations_bp.get("/overprivileged")
@cross_origin()
def list_over_privileged_users():
    """Return paginated over-privileged access findings for least-privilege remediation."""

    try:
        limit, offset = parse_pagination()
        results = get_over_privileged_users(limit=limit, offset=offset)
        return success_response(results)
    except Exception:
        return error_response("Unable to fetch over-privileged users.", 500, 500)


@violations_bp.post("/<int:violation_id>/status")
@cross_origin()
def set_violation_status(violation_id: int):
    """Update SoD violation status to `remediated` or `accepted` for workflow tracking."""

    try:
        payload = request.get_json(silent=True) or {}
        requested_status = payload.get("status")
        if requested_status not in {"remediated", "accepted"}:
            return error_response("Invalid status value.", 400, 400)

        updated = update_violation_status(violation_id=violation_id, new_status=requested_status)
        return success_response(updated)
    except LookupError:
        return error_response("Violation not found.", 404, 404)
    except ValueError:
        return error_response("Invalid status value.", 400, 400)
    except Exception:
        return error_response("Unable to update violation status.", 500, 500)

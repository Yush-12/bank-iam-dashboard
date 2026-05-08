"""User inventory and user-detail API routes for IAM certification workflows."""

from __future__ import annotations

from flask import Blueprint, request
from flask_cors import cross_origin

from ..engine.api_service import get_user_detail, get_users
from .utils import error_response, parse_pagination, success_response


users_bp = Blueprint("users", __name__, url_prefix="/api/users")


@users_bp.get("/", strict_slashes=False)
@cross_origin()
def list_users():
    """Return paginated users with optional department/status filters and role counts."""

    try:
        department = request.args.get("department")
        status = request.args.get("status")
        limit, offset = parse_pagination()
        data = get_users(
            department=department,
            status=status,
            limit=limit,
            offset=offset,
        )
        return success_response(data)
    except Exception:
        return error_response("Unable to fetch users.", 500, 500)


@users_bp.get("/<int:user_id>")
@cross_origin()
def get_user(user_id: int):
    """Return detailed user context including roles, permissions, logs, and risk indicators."""

    try:
        detail = get_user_detail(user_id=user_id)
        if detail is None:
            return error_response("User not found.", 404, 404)
        return success_response(detail)
    except Exception:
        return error_response("Unable to fetch user details.", 500, 500)

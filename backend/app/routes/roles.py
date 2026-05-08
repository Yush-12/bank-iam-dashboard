"""Role and RBAC analytics API routes for access model governance."""

from __future__ import annotations

from flask import Blueprint
from flask_cors import cross_origin

from ..engine.api_service import get_consolidation_candidates, get_rbac_health, get_roles
from .utils import error_response, parse_pagination, success_response


roles_bp = Blueprint("roles", __name__, url_prefix="/api/roles")
rbac_bp = Blueprint("rbac", __name__, url_prefix="/api/rbac")


@roles_bp.get("/", strict_slashes=False)
@cross_origin()
def list_roles():
    """Return paginated roles with permission bundles and active user counts."""

    try:
        limit, offset = parse_pagination()
        data = get_roles(limit=limit, offset=offset)
        return success_response(data)
    except Exception:
        return error_response("Unable to fetch roles.", 500, 500)


@rbac_bp.get("/consolidation")
@cross_origin()
def get_consolidation():
    """Return paginated role-consolidation candidates based on permission overlap."""

    try:
        limit, offset = parse_pagination()
        data = get_consolidation_candidates(limit=limit, offset=offset)
        return success_response(data)
    except Exception:
        return error_response("Unable to fetch role consolidation candidates.", 500, 500)


@rbac_bp.get("/health")
@cross_origin()
def get_health():
    """Return RBAC health score, grade, and deductions breakdown."""

    try:
        data = get_rbac_health()
        return success_response(data)
    except Exception:
        return error_response("Unable to fetch RBAC health.", 500, 500)

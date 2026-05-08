"""Phase 1 blueprint stubs for IAM backend routes."""

from flask import Blueprint, jsonify


health_bp = Blueprint("health", __name__)
users_bp = Blueprint("users", __name__, url_prefix="/api/users")
roles_bp = Blueprint("roles", __name__, url_prefix="/api/roles")
reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")
detections_bp = Blueprint("detections", __name__, url_prefix="/api/detections")


@health_bp.get("/health")
def health_check():
    """Return a simple readiness response."""

    return jsonify({"status": "ok", "service": "iam-access-review-backend"}), 200

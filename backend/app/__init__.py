"""Flask application factory for IAM Access Review APIs with middleware and routes."""

from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .middleware import health_bp, register_request_middleware
from .models import db
from .routes import (
    analysis_bp,
    dashboard_bp,
    rbac_bp,
    report_bp,
    roles_bp,
    users_bp,
    violations_bp,
    settings_bp,
)
from .seeder import seed_database


def _register_blueprints(app: Flask) -> None:
    """Register all Phase 3 API blueprints with the Flask application."""

    blueprint_registry = [
        health_bp,
        dashboard_bp,
        violations_bp,
        users_bp,
        roles_bp,
        rbac_bp,
        analysis_bp,
        report_bp,
        settings_bp,
    ]
    for blueprint in blueprint_registry:
        app.register_blueprint(blueprint)


def create_app(test_config: dict | None = None) -> Flask:
    """Create and configure the Flask application instance."""

    app = Flask(__name__)
    import os
    db_path = "/tmp/iam_review.db"
    if os.name == "nt":
        # On Windows, use a local path if /tmp doesn't exist or map correctly
        db_path = os.path.abspath("iam_review.db")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = False

    if test_config:
        app.config.update(test_config)

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
    origins = [o.strip().rstrip("/") for o in FRONTEND_URL.split(",")]
    CORS(app, resources={r"/api/*": {"origins": origins}})
    register_request_middleware(app)
    _register_blueprints(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        if not app.config.get("TESTING", False):
            seed_database()

    return app

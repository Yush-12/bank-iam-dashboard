"""Analysis API routes for on-demand IAM detection engine execution."""

from __future__ import annotations

import time

from flask import Blueprint
from flask_cors import cross_origin

from ..engine import run_full_analysis
from .utils import error_response, success_response


analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/analysis")


@analysis_bp.post("/run")
@cross_origin()
def run_analysis():
    """Run full IAM analysis with a short delay for frontend loading-state simulation."""

    try:
        time.sleep(2)
        result = run_full_analysis()
        return success_response(result)
    except Exception:
        return error_response("Unable to run analysis.", 500, 500)

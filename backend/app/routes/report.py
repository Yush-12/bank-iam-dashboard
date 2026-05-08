"""Report API routes for downloadable IAM certification artifacts."""

from __future__ import annotations

from importlib import import_module

from flask import Blueprint, Response
from flask_cors import cross_origin

from .utils import error_response


report_bp = Blueprint("report", __name__, url_prefix="/api/report")


def _load_generate_pdf_report():
    """Dynamically resolve Phase 4 PDF generator function from known module paths."""

    module_candidates = [
        "app.reporting",
        "app.report_generator",
        "app.engine.report_generator",
        "app.phase4.report_generator",
    ]

    for module_name in module_candidates:
        try:
            module = import_module(module_name)
        except Exception:
            continue
        generator = getattr(module, "generate_pdf_report", None)
        if callable(generator):
            return generator
    return None


@report_bp.get("/generate")
@cross_origin()
def generate_report():
    """Generate and return the IAM access certification PDF as a file download."""

    try:
        generator = _load_generate_pdf_report()
        if generator is None:
            return error_response("Report generation is not available yet.", 501, 501)

        pdf_result = generator()
        if isinstance(pdf_result, bytes):
            pdf_bytes = pdf_result
        elif hasattr(pdf_result, "getvalue"):
            pdf_bytes = pdf_result.getvalue()
        else:
            return error_response("Report generation failed.", 500, 500)

        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=access_certification_report.pdf"
            },
        )
    except Exception:
        return error_response("Unable to generate report.", 500, 500)

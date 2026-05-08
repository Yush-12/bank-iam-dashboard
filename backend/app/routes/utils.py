"""Common API response and pagination helpers for Flask route blueprints."""

from __future__ import annotations

from datetime import datetime

from flask import jsonify, request


def now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""

    return datetime.utcnow().isoformat()


def success_response(data, status_code: int = 200):
    """Return a success envelope payload with standard metadata."""

    return (
        jsonify(
            {
                "success": True,
                "data": data,
                "timestamp": now_iso(),
            }
        ),
        status_code,
    )


def error_response(message: str, code: int, status_code: int | None = None):
    """Return an error envelope payload without exposing internal debug details."""

    http_status = status_code if status_code is not None else code
    return (
        jsonify(
            {
                "success": False,
                "error": message,
                "code": code,
                "timestamp": now_iso(),
            }
        ),
        http_status,
    )


def parse_pagination(default_limit: int = 50, default_offset: int = 0) -> tuple[int, int]:
    """Parse and sanitize `limit` and `offset` query parameters."""

    limit = request.args.get("limit", default_limit, type=int)
    offset = request.args.get("offset", default_offset, type=int)

    if limit is None:
        limit = default_limit
    if offset is None:
        offset = default_offset

    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    return limit, offset

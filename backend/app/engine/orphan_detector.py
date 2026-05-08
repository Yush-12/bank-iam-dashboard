"""Orphan-account detection supporting RBI IT Framework termination controls and ISO 27001 A.9."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import OrphanAccount, Role, User, UserRole, UserStatus


def _enum_value(value: Any) -> str:
    """Return enum `.value` when present, otherwise cast to string."""

    return value.value if hasattr(value, "value") else str(value)


def _days_since_termination(user: User, now: datetime) -> int:
    """Compute elapsed days from employment end date, defaulting to zero when unavailable."""

    if user.employment_end_date is None:
        return 0
    return max((now - user.employment_end_date).days, 0)


def _risk_level(days_since_termination: int) -> str:
    """Classify orphan-account risk based on stale access duration."""

    if days_since_termination > 90:
        return "critical"
    if days_since_termination > 30:
        return "high"
    return "medium"


def _collect_orphan_accounts(session, persist: bool) -> tuple[list[dict[str, Any]], bool]:
    """Collect orphan-account findings and optionally persist records."""

    now = datetime.utcnow()
    findings: list[dict[str, Any]] = []
    has_mutation = False

    inactive_users = (
        session.query(User)
        .filter(User.status.in_([UserStatus.terminated, UserStatus.suspended]))
        .all()
    )

    for user in inactive_users:
        active_assignments = (
            session.query(UserRole)
            .join(Role, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == user.id,
                UserRole.is_active.is_(True),
            )
            .all()
        )
        if not active_assignments:
            continue

        active_roles = sorted({assignment.role.name for assignment in active_assignments if assignment.role})
        active_systems = sorted(
            {
                assignment.role.system.name
                for assignment in active_assignments
                if assignment.role and assignment.role.system
            }
        )
        days = _days_since_termination(user, now)
        risk = _risk_level(days)

        if persist:
            orphan_record = session.query(OrphanAccount).filter_by(user_id=user.id).first()
            systems_csv = ", ".join(active_systems)
            if orphan_record is None:
                orphan_record = OrphanAccount(
                    user_id=user.id,
                    detected_at=now,
                    days_since_termination=days,
                    systems_still_active=systems_csv,
                )
                session.add(orphan_record)
                has_mutation = True
            else:
                orphan_record.detected_at = now
                orphan_record.days_since_termination = days
                orphan_record.systems_still_active = systems_csv
                has_mutation = True

        findings.append(
            {
                "user_id": user.id,
                "user_name": user.name,
                "employee_id": user.employee_id,
                "department": user.department,
                "user_status": _enum_value(user.status),
                "employment_end_date": (
                    user.employment_end_date.isoformat() if user.employment_end_date else None
                ),
                "days_since_termination": days,
                "active_roles": active_roles,
                "active_systems": active_systems,
                "risk_level": risk,
                "recommended_action": (
                    "Immediately disable all active sessions and revoke system access per RBI "
                    "IT Framework §5.1"
                ),
            }
        )

    return findings, has_mutation


def detect_orphan_accounts(db) -> list[dict[str, Any]]:
    """Detect inactive employees with active access and persist orphan findings for compliance evidence."""

    findings, has_mutation = _collect_orphan_accounts(db.session, persist=True)
    if has_mutation:
        db.session.commit()
    return findings


def get_orphan_summary(db) -> dict[str, int]:
    """Return orphan-account totals by risk level for remediation prioritization."""

    findings, _ = _collect_orphan_accounts(db.session, persist=False)
    summary = {"critical": 0, "high": 0, "medium": 0}
    for finding in findings:
        summary[finding["risk_level"]] += 1

    return {
        "total_orphan_accounts": len(findings),
        "critical": summary["critical"],
        "high": summary["high"],
        "medium": summary["medium"],
    }

"""API-facing engine services for IAM analytics under RBI IT Framework and ISO 27001 Annex A.9."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import joinedload

from ..models import (
    AccessLog,
    Permission,
    Role,
    RolePermission,
    SoDRule,
    SoDViolation,
    System,
    User,
    UserRole,
    UserStatus,
    ViolationStatus,
    db,
)
from .orphan_detector import detect_orphan_accounts, get_orphan_summary
from .privilege_analyser import detect_over_privileged_users, detect_role_explosion
from .role_consolidator import get_rbac_health_score, suggest_role_consolidation
from .sod_detector import detect_sod_violations, get_sod_summary


def _enum_value(value: Any) -> str:
    """Return enum `.value` when present, otherwise cast to string."""

    return value.value if hasattr(value, "value") else str(value)


def _paginate(items: list[dict[str, Any]], limit: int, offset: int) -> dict[str, Any]:
    """Apply offset-based pagination to an in-memory result set."""

    total = len(items)
    safe_offset = max(offset, 0)
    safe_limit = max(limit, 1)
    paged_items = items[safe_offset : safe_offset + safe_limit]
    return {
        "items": paged_items,
        "pagination": {
            "limit": safe_limit,
            "offset": safe_offset,
            "count": len(paged_items),
            "total": total,
        },
    }


def _get_active_role_name_for_permission(session, user_id: int, permission_id: int) -> str | None:
    """Resolve an active role name for a user-permission combination."""

    role = (
        session.query(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .filter(
            UserRole.user_id == user_id,
            UserRole.is_active.is_(True),
            RolePermission.permission_id == permission_id,
        )
        .order_by(Role.name.asc())
        .first()
    )
    return role.name if role else None


def _violation_to_dict(session, violation: SoDViolation) -> dict[str, Any]:
    """Serialize SoD violation model to API-friendly dict."""

    user = violation.user
    rule = violation.rule
    permission_a = rule.permission_a if rule else None
    permission_b = rule.permission_b if rule else None

    role_a_name = (
        _get_active_role_name_for_permission(session, user.id, permission_a.id)
        if user and permission_a
        else None
    )
    role_b_name = (
        _get_active_role_name_for_permission(session, user.id, permission_b.id)
        if user and permission_b
        else None
    )

    return {
        "violation_id": violation.id,
        "user_id": user.id if user else None,
        "user_name": user.name if user else None,
        "employee_id": user.employee_id if user else None,
        "department": user.department if user else None,
        "rule_id": rule.id if rule else None,
        "rule_description": rule.description if rule else None,
        "severity": _enum_value(rule.severity) if rule else None,
        "regulatory_reference": rule.regulatory_reference if rule else None,
        "permission_a": permission_a.name if permission_a else None,
        "permission_b": permission_b.name if permission_b else None,
        "role_a_name": role_a_name,
        "role_b_name": role_b_name,
        "recommended_action": violation.recommended_action,
        "status": _enum_value(violation.status),
        "detected_at": violation.detected_at.isoformat() if violation.detected_at else None,
    }


def get_dashboard_summary(db_session=db) -> dict[str, Any]:
    """Build dashboard summary metrics and compliance flags for executive monitoring."""

    detect_sod_violations(db_session)
    detect_orphan_accounts(db_session)

    session = db_session.session
    sod_summary = get_sod_summary(db_session)
    orphan_summary = get_orphan_summary(db_session)
    over_privileged_users = detect_over_privileged_users(db_session)
    role_explosion = detect_role_explosion(db_session)
    health_score = get_rbac_health_score(db_session)

    total_users = session.query(User).count()
    active_users = session.query(User).filter(User.status == UserStatus.active).count()
    terminated_users = session.query(User).filter(User.status == UserStatus.terminated).count()
    systems_monitored = session.query(System).count()
    total_roles = session.query(Role).count()

    compliance_flags: list[dict[str, str]] = []
    if sod_summary["critical"] > 0:
        compliance_flags.append(
            {
                "type": "sod",
                "message": (
                    "Critical SoD violations require immediate remediation per RBI IT Framework §3.2"
                ),
                "severity": "critical",
                "regulatory_ref": "RBI IT Framework §3.2 / ISO 27001 A.9.4.1",
            }
        )
    if orphan_summary["critical"] > 0 or orphan_summary["high"] > 0:
        compliance_flags.append(
            {
                "type": "orphan_account",
                "message": "Inactive employees retain active access and require immediate deprovisioning.",
                "severity": "high" if orphan_summary["critical"] == 0 else "critical",
                "regulatory_ref": "RBI IT Framework §5.1 / ISO 27001 A.9.2.6",
            }
        )
    if len(over_privileged_users) > 0:
        compliance_flags.append(
            {
                "type": "over_privilege",
                "message": "Dormant privileged access detected; enforce least privilege recertification.",
                "severity": "high",
                "regulatory_ref": "RBI IT Framework §3.2 / ISO 27001 A.9.2.5",
            }
        )
    if role_explosion["role_explosion_score"] == "severe":
        compliance_flags.append(
            {
                "type": "rbac_design",
                "message": "RBAC role explosion is severe and increases SoD control complexity.",
                "severity": "high",
                "regulatory_ref": "ISO 27001 Annex A.9",
            }
        )

    return {
        "rbac_health_score": health_score,
        "total_users": total_users,
        "active_users": active_users,
        "terminated_users": terminated_users,
        "sod_violations": {
            "total": sod_summary["total_violations"],
            "critical": sod_summary["critical"],
            "high": sod_summary["high"],
            "medium": sod_summary["medium"],
        },
        "orphan_accounts": {
            "total": orphan_summary["total_orphan_accounts"],
            "critical": orphan_summary["critical"],
            "high": orphan_summary["high"],
            "medium": orphan_summary["medium"],
        },
        "over_privileged_users": len(over_privileged_users),
        "role_explosion": {
            "score": role_explosion["role_explosion_score"],
            "unique_combinations": role_explosion["total_unique_role_combinations"],
        },
        "last_analysis": datetime.utcnow().isoformat(),
        "systems_monitored": systems_monitored,
        "total_roles": total_roles,
        "compliance_flags": compliance_flags,
    }


def get_sod_violations(
    db_session=db,
    severity: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Return paginated SoD violations with optional severity and status filters."""

    detect_sod_violations(db_session)
    session = db_session.session

    query = session.query(SoDViolation).options(
        joinedload(SoDViolation.user),
        joinedload(SoDViolation.rule).joinedload(SoDRule.permission_a),
        joinedload(SoDViolation.rule).joinedload(SoDRule.permission_b),
    )

    if severity:
        query = query.join(SoDRule, SoDViolation.rule_id == SoDRule.id).filter(SoDRule.severity == severity)
    if status:
        query = query.filter(SoDViolation.status == status)

    query = query.order_by(SoDViolation.detected_at.desc(), SoDViolation.id.desc())
    total = query.count()
    violations = query.offset(max(offset, 0)).limit(max(limit, 1)).all()

    items = [_violation_to_dict(session, violation) for violation in violations]
    return {
        "items": items,
        "pagination": {
            "limit": max(limit, 1),
            "offset": max(offset, 0),
            "count": len(items),
            "total": total,
        },
    }


def update_violation_status(db_session=db, violation_id: int = 0, new_status: str = "") -> dict[str, Any]:
    """Update SoD violation lifecycle status for remediation workflows."""

    if new_status not in {"remediated", "accepted"}:
        raise ValueError("Invalid status value.")

    session = db_session.session
    violation = (
        session.query(SoDViolation)
        .options(
            joinedload(SoDViolation.user),
            joinedload(SoDViolation.rule).joinedload(SoDRule.permission_a),
            joinedload(SoDViolation.rule).joinedload(SoDRule.permission_b),
        )
        .filter(SoDViolation.id == violation_id)
        .first()
    )
    if violation is None:
        raise LookupError("Violation not found.")

    violation.status = ViolationStatus(new_status)
    session.commit()
    session.refresh(violation)
    return _violation_to_dict(session, violation)


def get_orphan_accounts(db_session=db, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Return paginated orphan-account findings for terminated/suspended employees."""

    findings = detect_orphan_accounts(db_session)
    findings = sorted(
        findings,
        key=lambda item: (item["days_since_termination"], item["user_name"]),
        reverse=True,
    )
    return _paginate(findings, limit=limit, offset=offset)


def get_over_privileged_users(db_session=db, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Return paginated over-privileged findings sorted by highest risk score."""

    findings = detect_over_privileged_users(db_session)
    findings = sorted(findings, key=lambda item: item["risk_score"], reverse=True)
    return _paginate(findings, limit=limit, offset=offset)


def get_users(
    db_session=db,
    department: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Return paginated user inventory with role counts and login recency."""

    session = db_session.session
    query = session.query(User)

    if department:
        query = query.filter(User.department == department)
    if status:
        query = query.filter(User.status == status)

    query = query.order_by(User.name.asc())
    total = query.count()
    users = query.offset(max(offset, 0)).limit(max(limit, 1)).all()

    items = []
    for user in users:
        role_count = (
            session.query(UserRole)
            .filter(
                UserRole.user_id == user.id,
                UserRole.is_active.is_(True),
            )
            .count()
        )
        items.append(
            {
                "id": user.id,
                "employee_id": user.employee_id,
                "name": user.name,
                "email": user.email,
                "department": user.department,
                "job_title": user.job_title,
                "status": _enum_value(user.status),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "role_count": role_count,
            }
        )

    return {
        "items": items,
        "pagination": {
            "limit": max(limit, 1),
            "offset": max(offset, 0),
            "count": len(items),
            "total": total,
        },
    }


def get_user_detail(db_session=db, user_id: int = 0) -> dict[str, Any] | None:
    """Return complete user access profile, role context, telemetry, and risk indicators."""

    detect_sod_violations(db_session)
    orphan_user_ids = {item["user_id"] for item in detect_orphan_accounts(db_session)}
    overprivileged_user_ids = {item["user_id"] for item in detect_over_privileged_users(db_session)}

    session = db_session.session
    user = (
        session.query(User)
        .options(
            joinedload(User.user_roles).joinedload(UserRole.role).joinedload(Role.system),
            joinedload(User.user_roles)
            .joinedload(UserRole.role)
            .joinedload(Role.role_permissions)
            .joinedload(RolePermission.permission)
            .joinedload(Permission.system),
            joinedload(User.access_logs).joinedload(AccessLog.system),
            joinedload(User.sod_violations).joinedload(SoDViolation.rule).joinedload(SoDRule.permission_a),
            joinedload(User.sod_violations).joinedload(SoDViolation.rule).joinedload(SoDRule.permission_b),
        )
        .filter(User.id == user_id)
        .first()
    )
    if user is None:
        return None

    roles = []
    permission_records: set[tuple[str, str, str]] = set()
    for assignment in sorted(user.user_roles, key=lambda item: item.assigned_date, reverse=True):
        role = assignment.role
        if role is None:
            continue
        roles.append(
            {
                "role_name": role.name,
                "system": role.system.name if role.system else None,
                "risk_level": _enum_value(role.risk_level),
                "assigned_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                "last_reviewed": (
                    assignment.last_reviewed_date.isoformat() if assignment.last_reviewed_date else None
                ),
                "is_active": assignment.is_active,
            }
        )
        for role_permission in role.role_permissions:
            permission = role_permission.permission
            if permission is None:
                continue
            permission_records.add(
                (
                    permission.name,
                    permission.system.name if permission.system else None,
                    permission.permission_type,
                )
            )

    permissions = [
        {
            "permission_name": permission_name,
            "system": system_name,
            "type": permission_type,
        }
        for permission_name, system_name, permission_type in sorted(permission_records)
    ]

    access_logs = []
    for access_log in sorted(user.access_logs, key=lambda item: item.system.name if item.system else ""):
        access_logs.append(
            {
                "system": access_log.system.name if access_log.system else None,
                "last_accessed": access_log.last_accessed.isoformat() if access_log.last_accessed else None,
                "access_count_90d": access_log.access_count_90d,
            }
        )

    violations = []
    for violation in sorted(user.sod_violations, key=lambda item: item.detected_at, reverse=True):
        violations.append(_violation_to_dict(session, violation))

    return {
        "user": user.to_dict(),
        "roles": roles,
        "permissions": permissions,
        "access_logs": access_logs,
        "violations": violations,
        "risk_summary": {
            "has_sod_violation": len(violations) > 0,
            "is_orphan": user.id in orphan_user_ids,
            "is_overprivileged": user.id in overprivileged_user_ids,
        },
    }


def get_roles(db_session=db, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Return paginated role catalog with permission bundles and active assignment counts."""

    session = db_session.session
    query = session.query(Role).options(
        joinedload(Role.system),
        joinedload(Role.user_roles),
        joinedload(Role.role_permissions).joinedload(RolePermission.permission),
    )
    query = query.order_by(Role.name.asc())

    total = query.count()
    roles = query.offset(max(offset, 0)).limit(max(limit, 1)).all()
    items: list[dict[str, Any]] = []

    for role in roles:
        permissions = [
            {
                "permission_name": role_permission.permission.name,
                "type": role_permission.permission.permission_type,
            }
            for role_permission in role.role_permissions
            if role_permission.permission is not None
        ]
        items.append(
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "risk_level": _enum_value(role.risk_level),
                "system": role.system.name if role.system else None,
                "permissions": sorted(permissions, key=lambda item: item["permission_name"]),
                "user_count": sum(1 for assignment in role.user_roles if assignment.is_active),
            }
        )

    return {
        "items": items,
        "pagination": {
            "limit": max(limit, 1),
            "offset": max(offset, 0),
            "count": len(items),
            "total": total,
        },
    }


def get_consolidation_candidates(db_session=db, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Return paginated role consolidation suggestions based on permission overlap."""

    suggestions = suggest_role_consolidation(db_session)
    return _paginate(suggestions, limit=limit, offset=offset)


def get_rbac_health(db_session=db) -> dict[str, Any]:
    """Return RBAC health score, grade, and controls-based deduction breakdown."""

    detect_sod_violations(db_session)
    detect_orphan_accounts(db_session)

    sod_summary = get_sod_summary(db_session)
    orphan_summary = get_orphan_summary(db_session)
    role_explosion = detect_role_explosion(db_session)
    over_privileged = detect_over_privileged_users(db_session)

    critical_sod_deduction = sod_summary["critical"] * 5
    high_sod_deduction = sod_summary["high"] * 3
    orphan_deduction = orphan_summary["total_orphan_accounts"] * 4
    role_explosion_deduction = 10 if role_explosion["role_explosion_score"] == "severe" else 5 if role_explosion["role_explosion_score"] == "moderate" else 0
    over_privileged_deduction = len(over_privileged) * 2

    score = get_rbac_health_score(db_session)

    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 40:
        grade = "C"
    elif score >= 20:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "breakdown": {
            "sod_critical_count": sod_summary["critical"],
            "sod_high_count": sod_summary["high"],
            "orphan_account_count": orphan_summary["total_orphan_accounts"],
            "role_explosion_score": role_explosion["role_explosion_score"],
            "over_privileged_count": len(over_privileged),
            "deductions": {
                "critical_sod": critical_sod_deduction,
                "high_sod": high_sod_deduction,
                "orphan_accounts": orphan_deduction,
                "role_explosion": role_explosion_deduction,
                "over_privileged": over_privileged_deduction,
            },
        },
    }


def get_db_health(db_session=db) -> dict[str, str]:
    """Perform a lightweight database connectivity check for health endpoints."""

    db_session.session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}

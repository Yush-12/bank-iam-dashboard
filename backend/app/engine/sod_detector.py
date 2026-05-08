"""SoD detection engine driven by RBI IT Framework and ISO 27001 Annex A.9 controls."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import (
    Role,
    RolePermission,
    SoDRule,
    SoDViolation,
    User,
    UserRole,
    ViolationStatus,
)


def _enum_value(value: Any) -> str:
    """Return enum `.value` when present, otherwise cast to string."""

    return value.value if hasattr(value, "value") else str(value)


def _risk_rank(role: Role | None) -> int:
    """Map role risk levels to comparable numeric ranks."""

    if role is None or role.risk_level is None:
        return 99
    rank_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    return rank_map.get(_enum_value(role.risk_level), 99)


def _pick_role(roles: dict[int, Role]) -> Role | None:
    """Select a deterministic representative role for reporting."""

    if not roles:
        return None
    return sorted(roles.values(), key=lambda item: (_risk_rank(item), item.name))[0]


def _recommended_action(severity: str, role_a: Role | None, role_b: Role | None) -> str:
    """Build a remediation recommendation aligned to compliance severity."""

    if severity == "critical":
        candidate_roles = [role for role in (role_a, role_b) if role is not None]
        if not candidate_roles:
            return "IMMEDIATE: Revoke conflicting role pending access review"
        lower_risk_role = sorted(candidate_roles, key=lambda item: (_risk_rank(item), item.name))[0]
        return f"IMMEDIATE: Revoke {lower_risk_role.name} pending access review"
    if severity == "high":
        return "Revoke within 5 business days per RBI IT Framework §3.2"
    return "Review and remediate within 30 days per ISO 27001 A.9.4"


def detect_sod_violations(db) -> list[dict[str, Any]]:
    """Detect SoD conflicts and persist findings as required by RBI/ISO maker-checker controls."""

    session = db.session
    now = datetime.utcnow()
    rules = session.query(SoDRule).all()
    findings: list[dict[str, Any]] = []
    created_new_finding = False

    for rule in rules:
        permission_a_matches = (
            session.query(UserRole.user_id, Role)
            .join(Role, UserRole.role_id == Role.id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .filter(
                UserRole.is_active.is_(True),
                RolePermission.permission_id == rule.permission_a_id,
            )
            .all()
        )
        permission_b_matches = (
            session.query(UserRole.user_id, Role)
            .join(Role, UserRole.role_id == Role.id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .filter(
                UserRole.is_active.is_(True),
                RolePermission.permission_id == rule.permission_b_id,
            )
            .all()
        )

        users_with_permission_a: dict[int, dict[int, Role]] = {}
        users_with_permission_b: dict[int, dict[int, Role]] = {}

        for user_id, role in permission_a_matches:
            users_with_permission_a.setdefault(user_id, {})[role.id] = role
        for user_id, role in permission_b_matches:
            users_with_permission_b.setdefault(user_id, {})[role.id] = role

        violated_user_ids = sorted(
            set(users_with_permission_a.keys()).intersection(users_with_permission_b.keys())
        )

        for user_id in violated_user_ids:
            user = session.get(User, user_id)
            if user is None:
                continue

            role_a = _pick_role(users_with_permission_a[user_id])
            role_b = _pick_role(users_with_permission_b[user_id])
            severity = _enum_value(rule.severity)
            recommendation = _recommended_action(severity, role_a, role_b)

            existing_violation = (
                session.query(SoDViolation)
                .filter_by(user_id=user.id, rule_id=rule.id)
                .first()
            )
            if existing_violation is None:
                existing_violation = SoDViolation(
                    user_id=user.id,
                    rule_id=rule.id,
                    detected_at=now,
                    status=ViolationStatus.open,
                    recommended_action=recommendation,
                )
                session.add(existing_violation)
                created_new_finding = True

            findings.append(
                {
                    "user_id": user.id,
                    "user_name": user.name,
                    "employee_id": user.employee_id,
                    "department": user.department,
                    "rule_id": rule.id,
                    "rule_description": rule.description,
                    "severity": severity,
                    "regulatory_reference": rule.regulatory_reference,
                    "permission_a": rule.permission_a.name if rule.permission_a else None,
                    "permission_b": rule.permission_b.name if rule.permission_b else None,
                    "role_a_name": role_a.name if role_a else None,
                    "role_b_name": role_b.name if role_b else None,
                    "recommended_action": recommendation,
                    "status": _enum_value(existing_violation.status),
                }
            )

    if created_new_finding:
        session.commit()

    return findings


def get_sod_summary(db) -> dict[str, Any]:
    """Summarize persisted SoD findings for RBI/ISO-aligned risk dashboards."""

    session = db.session
    violations = session.query(SoDViolation).filter(SoDViolation.status != ViolationStatus.remediated).all()
    if not violations:
        return {
            "total_violations": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "users_affected": 0,
            "systems_affected": [],
        }

    critical = 0
    high = 0
    medium = 0
    affected_users: set[int] = set()
    affected_systems: set[str] = set()

    for violation in violations:
        affected_users.add(violation.user_id)
        if violation.rule and violation.rule.permission_a and violation.rule.permission_a.system:
            affected_systems.add(violation.rule.permission_a.system.name)
        if violation.rule and violation.rule.permission_b and violation.rule.permission_b.system:
            affected_systems.add(violation.rule.permission_b.system.name)

        severity = _enum_value(violation.rule.severity) if violation.rule else ""
        if severity == "critical":
            critical += 1
        elif severity == "high":
            high += 1
        elif severity == "medium":
            medium += 1

    return {
        "total_violations": len(violations),
        "critical": critical,
        "high": high,
        "medium": medium,
        "users_affected": len(affected_users),
        "systems_affected": sorted(affected_systems),
    }

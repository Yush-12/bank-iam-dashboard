"""Privilege analytics for least-privilege enforcement under RBI IT Framework and ISO 27001 A.9."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil
from typing import Any

from sqlalchemy.orm import joinedload

from ..models import AccessLog, Role, RolePermission, User, UserRole


def _enum_value(value: Any) -> str:
    """Return enum `.value` when present, otherwise cast to string."""

    return value.value if hasattr(value, "value") else str(value)


def _is_admin_role(role: Role) -> bool:
    """Identify admin-like roles from naming and permission attributes."""

    if "admin" in role.name.lower():
        return True
    for role_permission in role.role_permissions:
        permission = role_permission.permission
        if permission is None:
            continue
        if permission.permission_type.lower() == "admin" or permission.name.startswith("admin_"):
            return True
    return False


def _is_unused_access(access_log: AccessLog | None, now: datetime) -> bool:
    """Return True when a system has no meaningful activity in the prior 90 days."""

    if access_log is None:
        return True
    if access_log.access_count_90d != 0:
        return False
    if access_log.last_accessed is None:
        return True
    return access_log.last_accessed <= now - timedelta(days=90)


def _risk_score(total_roles: int, total_systems: int, admin_roles: int, unused_admin_roles: int) -> int:
    """Score over-privilege risk from role volume and unused admin ratio."""

    role_component = min(total_roles * 8, 40)
    system_component = min(total_systems * 6, 30)
    if admin_roles > 0:
        unused_component = int((unused_admin_roles / admin_roles) * 30)
    else:
        unused_component = 0
    return max(1, min(100, role_component + system_component + unused_component))


def detect_over_privileged_users(db) -> list[dict[str, Any]]:
    """Detect users with excessive or dormant privileged access requiring remediation."""

    session = db.session
    now = datetime.utcnow()

    active_assignments = (
        session.query(UserRole)
        .options(
            joinedload(UserRole.user),
            joinedload(UserRole.role)
            .joinedload(Role.system),
            joinedload(UserRole.role)
            .joinedload(Role.role_permissions)
            .joinedload(RolePermission.permission),
        )
        .filter(UserRole.is_active.is_(True))
        .all()
    )

    logs = session.query(AccessLog).all()
    access_log_map: dict[tuple[int, int], AccessLog] = {
        (log.user_id, log.system_id): log for log in logs
    }

    assignments_by_user: dict[int, list[UserRole]] = defaultdict(list)
    for assignment in active_assignments:
        assignments_by_user[assignment.user_id].append(assignment)

    findings: list[dict[str, Any]] = []
    for user_id, assignments in assignments_by_user.items():
        user = assignments[0].user if assignments and assignments[0].user else session.get(User, user_id)
        if user is None:
            continue

        active_roles = [assignment.role for assignment in assignments if assignment.role is not None]
        systems = {role.system for role in active_roles if role.system is not None}
        system_names = {system.name for system in systems}

        unused_admin_roles: set[str] = set()
        systems_not_accessed_90d: set[str] = set()
        admin_role_count = 0

        for role in active_roles:
            system = role.system
            if system is None:
                continue
            access_log = access_log_map.get((user.id, system.id))
            is_unused = _is_unused_access(access_log, now)
            if is_unused:
                systems_not_accessed_90d.add(system.name)

            if _is_admin_role(role):
                admin_role_count += 1
                if is_unused:
                    unused_admin_roles.add(role.name)

        flag_for_unused_admin = len(unused_admin_roles) > 0
        flag_for_sprawl = len(system_names) > 4
        if not (flag_for_unused_admin or flag_for_sprawl):
            continue

        score = _risk_score(
            total_roles=len(active_roles),
            total_systems=len(system_names),
            admin_roles=admin_role_count,
            unused_admin_roles=len(unused_admin_roles),
        )

        if flag_for_unused_admin and flag_for_sprawl:
            recommendation = (
                "Revoke unused admin roles and reduce cross-system access breadth; complete "
                "recertification within 10 business days per RBI IT Framework §3.2."
            )
        elif flag_for_unused_admin:
            recommendation = (
                "Revoke unused admin roles and enforce least-privilege recertification per RBI "
                "IT Framework §3.2 and ISO 27001 Annex A.9."
            )
        else:
            recommendation = (
                "Rationalize role sprawl across systems and align access to business need under "
                "ISO 27001 Annex A.9."
            )

        findings.append(
            {
                "user_id": user.id,
                "user_name": user.name,
                "department": user.department,
                "total_active_roles": len(active_roles),
                "total_systems_with_access": len(system_names),
                "unused_admin_roles": sorted(unused_admin_roles),
                "systems_not_accessed_90d": sorted(systems_not_accessed_90d),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "risk_score": score,
                "recommended_action": recommendation,
            }
        )

    return sorted(findings, key=lambda item: item["risk_score"], reverse=True)


def detect_role_explosion(db) -> dict[str, Any]:
    """Assess role-model entropy by measuring unique active role-set combinations."""

    session = db.session
    users = session.query(User).all()
    total_users = len(users)
    if total_users == 0:
        return {
            "total_unique_role_combinations": 0,
            "users_with_unique_combinations": 0,
            "ideal_role_count_estimate": 0,
            "role_explosion_score": "none",
            "top_bloated_users": [],
        }

    role_name_map = {role.id: role.name for role in session.query(Role).all()}
    active_assignments = session.query(UserRole).filter(UserRole.is_active.is_(True)).all()

    roles_by_user: dict[int, set[int]] = {user.id: set() for user in users}
    for assignment in active_assignments:
        roles_by_user.setdefault(assignment.user_id, set()).add(assignment.role_id)

    users_by_role_set: dict[frozenset[int], list[User]] = defaultdict(list)
    for user in users:
        role_set = frozenset(roles_by_user.get(user.id, set()))
        users_by_role_set[role_set].append(user)

    total_unique_role_combinations = len(users_by_role_set)
    users_with_unique_combinations = sum(
        len(grouped_users)
        for grouped_users in users_by_role_set.values()
        if len(grouped_users) == 1
    )
    ideal_role_count_estimate = ceil(total_users / 3)
    unique_ratio = users_with_unique_combinations / total_users

    if total_unique_role_combinations > int(ideal_role_count_estimate * 1.5) or unique_ratio >= 0.45:
        role_explosion_score = "severe"
    elif total_unique_role_combinations > ideal_role_count_estimate or unique_ratio >= 0.25:
        role_explosion_score = "moderate"
    else:
        role_explosion_score = "none"

    bloated_users: list[dict[str, Any]] = []
    for role_set, grouped_users in users_by_role_set.items():
        if len(grouped_users) != 1:
            continue
        user = grouped_users[0]
        role_names = sorted(role_name_map[role_id] for role_id in role_set if role_id in role_name_map)
        bloated_users.append(
            {
                "user_name": user.name,
                "role_count": len(role_set),
                "roles": role_names,
            }
        )

    top_bloated_users = sorted(
        bloated_users,
        key=lambda item: (item["role_count"], item["user_name"]),
        reverse=True,
    )[:5]

    return {
        "total_unique_role_combinations": total_unique_role_combinations,
        "users_with_unique_combinations": users_with_unique_combinations,
        "ideal_role_count_estimate": ideal_role_count_estimate,
        "role_explosion_score": role_explosion_score,
        "top_bloated_users": top_bloated_users,
    }

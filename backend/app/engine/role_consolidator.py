"""Role consolidation and RBAC health scoring under RBI IT Framework and ISO 27001 Annex A.9."""

from __future__ import annotations

from itertools import combinations
from typing import Any

from sqlalchemy.orm import joinedload

from ..models import Role, RolePermission
from .orphan_detector import get_orphan_summary
from .privilege_analyser import detect_over_privileged_users, detect_role_explosion
from .sod_detector import get_sod_summary


def _role_permission_names(role: Role) -> set[str]:
    """Return a role's permission names as a set."""

    permission_names: set[str] = set()
    for role_permission in role.role_permissions:
        if role_permission.permission:
            permission_names.add(role_permission.permission.name)
    return permission_names


def _active_user_count(role: Role) -> int:
    """Count active assignments for a role."""

    return sum(1 for assignment in role.user_roles if assignment.is_active)


def suggest_role_consolidation(db) -> list[dict[str, Any]]:
    """Suggest role merges where permission overlap indicates RBAC simplification potential."""

    session = db.session
    roles = (
        session.query(Role)
        .options(
            joinedload(Role.role_permissions).joinedload(RolePermission.permission),
            joinedload(Role.user_roles),
        )
        .all()
    )

    suggestions: list[dict[str, Any]] = []
    for role_a, role_b in combinations(roles, 2):
        permissions_a = _role_permission_names(role_a)
        permissions_b = _role_permission_names(role_b)
        union_permissions = permissions_a.union(permissions_b)
        if not union_permissions:
            continue

        overlap_permissions = permissions_a.intersection(permissions_b)
        similarity = len(overlap_permissions) / len(union_permissions)
        if similarity < 0.6:
            continue

        unique_to_a = sorted(permissions_a - permissions_b)
        unique_to_b = sorted(permissions_b - permissions_a)
        users_on_a = _active_user_count(role_a)
        users_on_b = _active_user_count(role_b)
        estimated_user_impact = users_on_a + users_on_b

        if similarity >= 0.85:
            recommendation = (
                "High overlap: merge these roles into one baseline role and preserve any delta "
                "permissions as controlled exceptions."
            )
        else:
            recommendation = (
                "Consider consolidating into a parent role with optional add-on permissions to "
                "reduce RBAC complexity."
            )

        suggestions.append(
            {
                "role_a_id": role_a.id,
                "role_a_name": role_a.name,
                "role_b_id": role_b.id,
                "role_b_name": role_b.name,
                "similarity_score": round(similarity, 2),
                "shared_permissions": sorted(overlap_permissions),
                "unique_to_a": unique_to_a,
                "unique_to_b": unique_to_b,
                "users_on_a": users_on_a,
                "users_on_b": users_on_b,
                "consolidation_recommendation": recommendation,
                "estimated_impact": (
                    f"{estimated_user_impact} user assignments may be impacted by consolidation."
                ),
            }
        )

    return sorted(
        suggestions,
        key=lambda item: (item["similarity_score"], item["users_on_a"] + item["users_on_b"]),
        reverse=True,
    )


def get_rbac_health_score(db) -> int:
    """Compute a 0-100 RBAC health score using SoD, orphan, privilege, and role-model signals."""

    score = 100
    sod_summary = get_sod_summary(db)
    score -= sod_summary["critical"] * 5
    score -= sod_summary["high"] * 3

    orphan_count = get_orphan_summary(db)["total_orphan_accounts"]
    score -= orphan_count * 4

    role_explosion = detect_role_explosion(db)
    if role_explosion["role_explosion_score"] == "severe":
        score -= 10
    elif role_explosion["role_explosion_score"] == "moderate":
        score -= 5

    over_privileged_count = len(detect_over_privileged_users(db))
    score -= over_privileged_count * 2

    return max(0, score)

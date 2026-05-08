"""IAM analysis orchestration aligned to RBI IT Framework and ISO 27001 Annex A.9."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import db as orm_db
from .orphan_detector import detect_orphan_accounts
from .privilege_analyser import detect_over_privileged_users, detect_role_explosion
from .role_consolidator import get_rbac_health_score, suggest_role_consolidation
from .sod_detector import detect_sod_violations


def run_full_analysis(db=orm_db) -> dict[str, Any]:
    """Run all detection modules and return a consolidated IAM compliance payload."""

    sod_violations = detect_sod_violations(db)
    orphan_accounts = detect_orphan_accounts(db)
    over_privileged_users = detect_over_privileged_users(db)
    role_explosion = detect_role_explosion(db)
    consolidation_suggestions = suggest_role_consolidation(db)
    rbac_health_score = get_rbac_health_score(db)

    return {
        "sod_violations": sod_violations,
        "orphan_accounts": orphan_accounts,
        "over_privileged_users": over_privileged_users,
        "role_explosion": role_explosion,
        "consolidation_suggestions": consolidation_suggestions,
        "rbac_health_score": rbac_health_score,
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }

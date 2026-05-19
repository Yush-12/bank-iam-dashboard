from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime, timedelta

from .models import (
    AccessLog,
    CriticalityLevel,
    OrphanAccount,
    Permission,
    RiskLevel,
    Role,
    RolePermission,
    SoDRule,
    SoDSeverity,
    SoDViolation,
    System,
    User,
    UserRole,
    UserStatus,
    db,
)


SYSTEM_DEFINITIONS = [
    {
        "name": "Core Banking System (CBS)",
        "description": "Primary core banking ledger and customer account servicing platform.",
        "criticality": CriticalityLevel.critical,
        "system_type": "core_banking",
    },
    {
        "name": "SWIFT Payment Gateway",
        "description": "Cross-border SWIFT messaging and payment authorization platform.",
        "criticality": CriticalityLevel.critical,
        "system_type": "payment",
    },
    {
        "name": "HR Portal",
        "description": "Employee records, compensation workflows, and HR self-service portal.",
        "criticality": CriticalityLevel.medium,
        "system_type": "hr",
    },
    {
        "name": "Active Directory",
        "description": "Enterprise identity directory for authentication and authorization.",
        "criticality": CriticalityLevel.high,
        "system_type": "directory",
    },
    {
        "name": "FINACLE",
        "description": "Loan origination and branch banking operations platform.",
        "criticality": CriticalityLevel.critical,
        "system_type": "core_banking",
    },
    {
        "name": "Treasury Management System",
        "description": "Treasury transfers, liquidity management, and market settlements platform.",
        "criticality": CriticalityLevel.high,
        "system_type": "payment",
    },
]


PERMISSION_DEFINITIONS = {
    "Core Banking System (CBS)": [
        ("initiate_payment", "initiate", "Initiate outgoing CBS payment transactions."),
        ("approve_payment", "approve", "Approve CBS payment transactions."),
        ("view_account", "view", "View customer account details in CBS."),
        ("modify_account", "admin", "Modify account master data in CBS."),
        ("delete_account", "delete", "Delete account artifacts in CBS."),
        ("admin_cbs", "admin", "Full CBS administration capabilities."),
    ],
    "SWIFT Payment Gateway": [
        ("initiate_swift", "initiate", "Initiate SWIFT transfer messages."),
        ("approve_swift", "approve", "Approve SWIFT transfer messages."),
        ("view_swift_logs", "view", "View SWIFT message and exception logs."),
        ("admin_swift", "admin", "Full SWIFT gateway administration capabilities."),
    ],
    "HR Portal": [
        ("view_salary", "view", "View salary and compensation records."),
        ("modify_salary", "admin", "Modify salary and compensation records."),
        ("view_employee", "view", "View employee master and profile records."),
        ("admin_hr", "admin", "Full HR portal administration capabilities."),
    ],
    "Active Directory": [
        ("create_user_ad", "admin", "Create identities in Active Directory."),
        ("delete_user_ad", "delete", "Delete identities from Active Directory."),
        ("reset_password", "admin", "Reset enterprise passwords in Active Directory."),
        ("admin_ad", "admin", "Full Active Directory administration capabilities."),
    ],
    "FINACLE": [
        ("initiate_loan", "initiate", "Initiate retail and corporate loan disbursements."),
        ("approve_loan", "approve", "Approve retail and corporate loan disbursements."),
        ("view_loan", "view", "View loan portfolios and repayment schedules."),
        ("admin_finacle", "admin", "Full FINACLE administration capabilities."),
    ],
    "Treasury Management System": [
        ("initiate_transfer", "initiate", "Initiate treasury fund transfers."),
        ("approve_transfer", "approve", "Approve treasury fund transfers."),
        ("view_treasury", "view", "View treasury positions and transfer reports."),
        ("admin_treasury", "admin", "Full treasury system administration capabilities."),
    ],
}


SOD_RULE_DEFINITIONS = [
    {
        "permission_a": "initiate_payment",
        "permission_b": "approve_payment",
        "description": "Payment initiation and approval must be segregated to prevent fraud.",
        "severity": SoDSeverity.critical,
        "regulatory_reference": "RBI IT Framework Sec.3.2 / ISO 27001 A.9.4.1",
    },
    {
        "permission_a": "initiate_swift",
        "permission_b": "approve_swift",
        "description": "SWIFT message initiation and approval cannot be held by the same user.",
        "severity": SoDSeverity.critical,
        "regulatory_reference": "RBI IT Framework Sec.3.2 / SWIFT CSCF v2023",
    },
    {
        "permission_a": "initiate_loan",
        "permission_b": "approve_loan",
        "description": "Loan initiation and sanction approval must be separated by control design.",
        "severity": SoDSeverity.critical,
        "regulatory_reference": "RBI IT Framework Sec.4.1 / ISO 27001 A.9.2.3",
    },
    {
        "permission_a": "initiate_transfer",
        "permission_b": "approve_transfer",
        "description": "Treasury transfer initiation and approval require maker-checker segregation.",
        "severity": SoDSeverity.high,
        "regulatory_reference": "RBI IT Framework Sec.3.2",
    },
    {
        "permission_a": "modify_salary",
        "permission_b": "approve_payment",
        "description": "Compensation edits combined with payment approval introduce fraud risk.",
        "severity": SoDSeverity.high,
        "regulatory_reference": "ISO 27001 A.9.4.2",
    },
    {
        "permission_a": "admin_cbs",
        "permission_b": "initiate_payment",
        "description": "CBS administrators should not initiate financial transactions directly.",
        "severity": SoDSeverity.high,
        "regulatory_reference": "ISO 27001 A.9.2.3",
    },
    {
        "permission_a": "delete_account",
        "permission_b": "approve_payment",
        "description": "Account deletion and payment approval pairing weakens audit assurance.",
        "severity": SoDSeverity.medium,
        "regulatory_reference": "ISO 27001 A.9.4.1",
    },
]


ROLE_DEFINITIONS = [
    {
        "name": "Teller",
        "description": "Frontline teller access for routine branch transactions.",
        "risk_level": RiskLevel.low,
        "system": "Core Banking System (CBS)",
        "permissions": ["initiate_payment", "view_account"],
    },
    {
        "name": "Senior Teller",
        "description": "Senior teller role with wider account servicing actions.",
        "risk_level": RiskLevel.medium,
        "system": "Core Banking System (CBS)",
        "permissions": ["initiate_payment", "view_account", "modify_account"],
    },
    {
        "name": "Branch Manager",
        "description": "Branch manager approval authority for CBS operations.",
        "risk_level": RiskLevel.high,
        "system": "Core Banking System (CBS)",
        "permissions": ["approve_payment", "view_account", "modify_account"],
    },
    {
        "name": "Payment Ops",
        "description": "Operations maker role for CBS payment processing.",
        "risk_level": RiskLevel.high,
        "system": "Core Banking System (CBS)",
        "permissions": ["initiate_payment", "view_account"],
    },
    {
        "name": "Payment Approver",
        "description": "Checker role for CBS payment authorization workflows.",
        "risk_level": RiskLevel.high,
        "system": "Core Banking System (CBS)",
        "permissions": ["approve_payment", "view_account"],
    },
    {
        "name": "SWIFT Operator",
        "description": "Maker role for cross-border SWIFT transfer instructions.",
        "risk_level": RiskLevel.high,
        "system": "SWIFT Payment Gateway",
        "permissions": ["initiate_swift", "view_swift_logs"],
    },
    {
        "name": "SWIFT Approver",
        "description": "Checker role for SWIFT transfer release controls.",
        "risk_level": RiskLevel.critical,
        "system": "SWIFT Payment Gateway",
        "permissions": ["approve_swift", "view_swift_logs"],
    },
    {
        "name": "HR Executive",
        "description": "HR operations role with employee and salary read access.",
        "risk_level": RiskLevel.medium,
        "system": "HR Portal",
        "permissions": ["view_employee", "view_salary"],
    },
    {
        "name": "HR Manager",
        "description": "HR manager role with salary maintenance authority.",
        "risk_level": RiskLevel.high,
        "system": "HR Portal",
        "permissions": ["view_employee", "view_salary", "modify_salary", "admin_hr"],
    },
    {
        "name": "IT Admin",
        "description": "IT operations role managing enterprise identity lifecycle tasks.",
        "risk_level": RiskLevel.high,
        "system": "Active Directory",
        "permissions": ["create_user_ad", "reset_password"],
    },
    {
        "name": "IT Security Analyst",
        "description": "Security analyst role for controlled password and identity interventions.",
        "risk_level": RiskLevel.medium,
        "system": "Active Directory",
        "permissions": ["reset_password"],
    },
    {
        "name": "Loan Officer",
        "description": "Loan processing maker role in FINACLE.",
        "risk_level": RiskLevel.high,
        "system": "FINACLE",
        "permissions": ["initiate_loan", "view_loan"],
    },
    {
        "name": "Loan Approver",
        "description": "Loan sanction checker role in FINACLE.",
        "risk_level": RiskLevel.high,
        "system": "FINACLE",
        "permissions": ["approve_loan", "view_loan"],
    },
    {
        "name": "Treasury Analyst",
        "description": "Treasury operations maker role for fund transfers.",
        "risk_level": RiskLevel.high,
        "system": "Treasury Management System",
        "permissions": ["initiate_transfer", "view_treasury"],
    },
    {
        "name": "Treasury Approver",
        "description": "Treasury checker role for high-value transfer approvals.",
        "risk_level": RiskLevel.high,
        "system": "Treasury Management System",
        "permissions": ["approve_transfer", "view_treasury"],
    },
    {
        "name": "Compliance Officer",
        "description": "Compliance visibility role for CBS access attestations.",
        "risk_level": RiskLevel.medium,
        "system": "Core Banking System (CBS)",
        "permissions": ["view_account"],
    },
    {
        "name": "Audit Viewer",
        "description": "Read-only SWIFT audit review role for internal audit.",
        "risk_level": RiskLevel.low,
        "system": "SWIFT Payment Gateway",
        "permissions": ["view_swift_logs"],
    },
    {
        "name": "CBS Admin",
        "description": "Privileged administrator for core banking maintenance.",
        "risk_level": RiskLevel.critical,
        "system": "Core Banking System (CBS)",
        "permissions": ["admin_cbs", "modify_account", "delete_account", "approve_payment"],
    },
    {
        "name": "FINACLE Admin",
        "description": "Privileged administrator for FINACLE platform operations.",
        "risk_level": RiskLevel.critical,
        "system": "FINACLE",
        "permissions": ["admin_finacle", "approve_loan", "view_loan"],
    },
    {
        "name": "AD Administrator",
        "description": "Privileged administrator for directory governance controls.",
        "risk_level": RiskLevel.critical,
        "system": "Active Directory",
        "permissions": ["admin_ad", "create_user_ad", "delete_user_ad", "reset_password"],
    },
]


ACTIVE_USER_PROFILES = [
    ("FCI1001", "Priya Sharma", "Retail Banking", "Relationship Banker"),
    ("FCI1002", "Arjun Mehta", "IT Security", "Senior IAM Engineer"),
    ("FCI1003", "Divya Iyer", "IT Security", "Identity Platform Lead"),
    ("FCI1004", "Rahul Verma", "Operations", "Payment Operations Analyst"),
    ("FCI1005", "Sneha Nair", "Operations", "SWIFT Operations Analyst"),
    ("FCI1006", "Karan Malhotra", "Retail Banking", "Loan Operations Officer"),
    ("FCI1007", "Neha Kapoor", "Treasury", "Treasury Desk Analyst"),
    ("FCI1008", "Vikram Rao", "IT Security", "Privileged Access Specialist"),
    ("FCI1009", "Aisha Khan", "Compliance", "Compliance Analyst"),
    ("FCI1010", "Rohan Kulkarni", "Retail Banking", "Branch Operations Manager"),
    ("FCI1011", "Pooja Menon", "Retail Banking", "Senior Teller"),
    ("FCI1012", "Sandeep Reddy", "Operations", "Payments Control Executive"),
    ("FCI1013", "Ananya Bose", "Operations", "SWIFT Desk Operator"),
    ("FCI1014", "Harsh Patel", "Retail Banking", "Loan Processing Officer"),
    ("FCI1015", "Meera Joshi", "Retail Banking", "Credit Sanction Officer"),
    ("FCI1016", "Nikhil Bansal", "Treasury", "Treasury Analyst"),
    ("FCI1017", "Kavya Srinivasan", "Treasury", "Treasury Control Officer"),
    ("FCI1018", "Manish Gupta", "Compliance", "Regulatory Compliance Officer"),
    ("FCI1019", "Ishita Chawla", "Compliance", "Internal Audit Analyst"),
    ("FCI1020", "Aditya Narang", "IT Security", "Cybersecurity Analyst"),
    ("FCI1021", "Ritu Agarwal", "HR", "HR Business Partner"),
    ("FCI1022", "Varun Desai", "IT Security", "Infrastructure Administrator"),
    ("FCI1023", "Shreya Pillai", "HR", "Compensation Manager"),
    ("FCI1024", "Gautam Banerjee", "Operations", "Payment Authorization Officer"),
    ("FCI1025", "Tanvi Arora", "Retail Banking", "Branch Teller"),
]


TERMINATED_USER_PROFILES = [
    ("FCI1026", "Mohit Saini", "Operations", "Payment Ops Executive"),
    ("FCI1027", "Lakshmi Subramanian", "HR", "HR Executive"),
    ("FCI1028", "Prakash Nambiar", "IT Security", "Directory Operations Engineer"),
    ("FCI1029", "Sonal Bhatia", "Compliance", "Audit Support Officer"),
    ("FCI1030", "Dinesh Choudhary", "Retail Banking", "Loan Documentation Specialist"),
]


ON_LEAVE_USER_PROFILES = [
    ("FCI1031", "Anil Thomas", "Operations", "SWIFT Control Associate"),
    ("FCI1032", "Bhavna Krishnan", "Treasury", "Treasury Settlements Analyst"),
    ("FCI1033", "Deepak Sehgal", "Compliance", "Policy Monitoring Specialist"),
]


SUSPENDED_USER_PROFILES = [
    ("FCI1034", "Komal Arvind", "HR", "Compensation Analyst"),
    ("FCI1035", "Yashwant Singh", "IT Security", "Security Operations Specialist"),
]


STALE_ACTIVE_USERS = {
    "Arjun Mehta",
    "Divya Iyer",
    "Vikram Rao",
    "Pooja Menon",
    "Harsh Patel",
    "Nikhil Bansal",
    "Aditya Narang",
    "Gautam Banerjee",
}


OVER_PRIVILEGED_USERS = {"Arjun Mehta", "Divya Iyer", "Vikram Rao"}


ORPHAN_CANDIDATES = {
    "Mohit Saini",
    "Lakshmi Subramanian",
    "Prakash Nambiar",
    "Anil Thomas",
    "Bhavna Krishnan",
}


ROLE_ASSIGNMENTS = {
    "Priya Sharma": ["Teller"],
    "Arjun Mehta": ["CBS Admin", "FINACLE Admin", "AD Administrator", "HR Manager"],
    "Divya Iyer": ["CBS Admin", "FINACLE Admin", "AD Administrator", "HR Manager"],
    "Rahul Verma": ["Payment Ops", "Payment Approver"],
    "Sneha Nair": ["SWIFT Operator", "SWIFT Approver"],
    "Karan Malhotra": ["Loan Officer", "Loan Approver"],
    "Neha Kapoor": ["Treasury Analyst", "Treasury Approver"],
    "Vikram Rao": ["CBS Admin", "FINACLE Admin", "AD Administrator", "HR Manager"],
    "Aisha Khan": ["Compliance Officer"],
    "Rohan Kulkarni": ["Branch Manager"],
    "Pooja Menon": ["Senior Teller"],
    "Sandeep Reddy": ["Payment Ops"],
    "Ananya Bose": ["SWIFT Operator"],
    "Harsh Patel": ["Loan Officer"],
    "Meera Joshi": ["Loan Approver"],
    "Nikhil Bansal": ["Treasury Analyst"],
    "Kavya Srinivasan": ["Treasury Approver"],
    "Manish Gupta": ["Compliance Officer"],
    "Ishita Chawla": ["Audit Viewer"],
    "Aditya Narang": ["IT Security Analyst"],
    "Ritu Agarwal": ["HR Executive"],
    "Varun Desai": ["IT Admin"],
    "Shreya Pillai": ["HR Manager"],
    "Gautam Banerjee": ["Payment Approver"],
    "Tanvi Arora": ["Teller"],
    "Mohit Saini": ["Payment Ops"],
    "Lakshmi Subramanian": ["HR Executive"],
    "Prakash Nambiar": ["IT Admin"],
    "Sonal Bhatia": ["Audit Viewer"],
    "Dinesh Choudhary": ["Loan Officer"],
    "Anil Thomas": ["SWIFT Operator"],
    "Bhavna Krishnan": ["Treasury Analyst"],
    "Deepak Sehgal": ["Compliance Officer"],
    "Komal Arvind": ["HR Executive"],
    "Yashwant Singh": ["IT Security Analyst"],
}


def _create_systems() -> dict[str, System]:
    """Create and persist system rows."""

    systems: dict[str, System] = {}
    for row in SYSTEM_DEFINITIONS:
        system = System(**row)
        db.session.add(system)
        systems[system.name] = system
    db.session.flush()
    return systems


def _create_permissions(systems: dict[str, System]) -> dict[str, Permission]:
    """Create and persist permission rows mapped by permission name."""

    permissions: dict[str, Permission] = {}
    for system_name, permission_rows in PERMISSION_DEFINITIONS.items():
        for permission_name, permission_type, description in permission_rows:
            permission = Permission(
                name=permission_name,
                description=description,
                permission_type=permission_type,
                system=systems[system_name],
            )
            db.session.add(permission)
            permissions[permission.name] = permission
    db.session.flush()
    return permissions


def _create_sod_rules(permissions: dict[str, Permission]) -> None:
    """Create and persist SoD rules based on permission pairs."""

    for row in SOD_RULE_DEFINITIONS:
        db.session.add(
            SoDRule(
                permission_a=permissions[row["permission_a"]],
                permission_b=permissions[row["permission_b"]],
                description=row["description"],
                severity=row["severity"],
                regulatory_reference=row["regulatory_reference"],
            )
        )
    db.session.flush()


def _create_roles(systems: dict[str, System]) -> dict[str, Role]:
    """Create and persist role rows mapped by role name."""

    roles: dict[str, Role] = {}
    for row in ROLE_DEFINITIONS:
        role = Role(
            name=row["name"],
            description=row["description"],
            risk_level=row["risk_level"],
            system=systems[row["system"]],
        )
        db.session.add(role)
        roles[role.name] = role
    db.session.flush()
    return roles


def _map_role_permissions(roles: dict[str, Role], permissions: dict[str, Permission]) -> None:
    """Create role-permission associations for all seeded roles."""

    for row in ROLE_DEFINITIONS:
        role = roles[row["name"]]
        for permission_name in row["permissions"]:
            db.session.add(RolePermission(role=role, permission=permissions[permission_name]))
    db.session.flush()


def _build_email(name: str) -> str:
    """Build a deterministic corporate email for mock users."""

    return f"{name.lower().replace(' ', '.')}@bank.com"


def _create_users(now: datetime) -> dict[str, User]:
    """Create and persist users across active, terminated, on-leave, and suspended states."""

    users: dict[str, User] = {}

    for employee_id, name, department, job_title in ACTIVE_USER_PROFILES:
        if name in STALE_ACTIVE_USERS:
            last_login = now - timedelta(days=random.randint(91, 180))
        else:
            last_login = now - timedelta(days=random.randint(1, 60))
        user = User(
            employee_id=employee_id,
            name=name,
            email=_build_email(name),
            department=department,
            job_title=job_title,
            status=UserStatus.active,
            employment_end_date=None,
            last_login=last_login,
            created_at=now - timedelta(days=random.randint(120, 900)),
        )
        db.session.add(user)
        users[name] = user

    for employee_id, name, department, job_title in TERMINATED_USER_PROFILES:
        end_date = now - timedelta(days=random.randint(30, 180))
        user = User(
            employee_id=employee_id,
            name=name,
            email=_build_email(name),
            department=department,
            job_title=job_title,
            status=UserStatus.terminated,
            employment_end_date=end_date,
            last_login=now - timedelta(days=random.randint(90, 300)),
            created_at=now - timedelta(days=random.randint(300, 1200)),
        )
        db.session.add(user)
        users[name] = user

    for employee_id, name, department, job_title in ON_LEAVE_USER_PROFILES:
        user = User(
            employee_id=employee_id,
            name=name,
            email=_build_email(name),
            department=department,
            job_title=job_title,
            status=UserStatus.on_leave,
            employment_end_date=None,
            last_login=now - timedelta(days=random.randint(40, 170)),
            created_at=now - timedelta(days=random.randint(150, 1000)),
        )
        db.session.add(user)
        users[name] = user

    for employee_id, name, department, job_title in SUSPENDED_USER_PROFILES:
        user = User(
            employee_id=employee_id,
            name=name,
            email=_build_email(name),
            department=department,
            job_title=job_title,
            status=UserStatus.suspended,
            employment_end_date=None,
            last_login=now - timedelta(days=random.randint(50, 200)),
            created_at=now - timedelta(days=random.randint(180, 1000)),
        )
        db.session.add(user)
        users[name] = user

    db.session.flush()
    return users


def _assign_roles(users: dict[str, User], roles: dict[str, Role], now: datetime) -> dict[str, set[str]]:
    """Assign roles to users and return active system assignments per user."""

    assigned_by_options = [
        "System Provisioning Bot",
        "IT Security Office",
        "Compliance Desk",
        "Operations Control Team",
        "HR Access Team",
    ]
    user_active_systems: dict[str, set[str]] = defaultdict(set)

    for user_name, role_names in ROLE_ASSIGNMENTS.items():
        user = users[user_name]
        for role_name in role_names:
            role = roles[role_name]
            assigned_date = now - timedelta(days=random.randint(45, 540))
            is_active = user.status == UserStatus.active or user_name in ORPHAN_CANDIDATES

            if random.random() < 0.8:
                reviewed_lag_days = random.randint(10, 180)
                last_reviewed_date = min(now - timedelta(days=1), assigned_date + timedelta(days=reviewed_lag_days))
            else:
                last_reviewed_date = None

            db.session.add(
                UserRole(
                    user=user,
                    role=role,
                    assigned_date=assigned_date,
                    last_reviewed_date=last_reviewed_date,
                    assigned_by=random.choice(assigned_by_options),
                    is_active=is_active,
                )
            )
            if is_active:
                user_active_systems[user_name].add(role.system.name)

    db.session.flush()
    return user_active_systems


def _create_access_logs(
    users: dict[str, User],
    systems: dict[str, System],
    user_active_systems: dict[str, set[str]],
    now: datetime,
) -> None:
    """Create access logs for every user-system combination."""

    stale_system_targets: dict[str, set[str]] = {}
    for name in OVER_PRIVILEGED_USERS:
        assigned_systems = sorted(user_active_systems.get(name, set()))
        stale_system_targets[name] = set(assigned_systems[:4])

    for user_name, user in users.items():
        for system in systems.values():
            if user.status == UserStatus.active:
                if user_name in OVER_PRIVILEGED_USERS and system.name in stale_system_targets[user_name]:
                    access_count = 0
                    last_accessed = now - timedelta(days=random.randint(91, 240))
                else:
                    access_count = random.randint(1, 200)
                    last_accessed = now - timedelta(days=random.randint(1, 30))
            elif user.status == UserStatus.terminated:
                access_count = random.randint(0, 10)
                last_accessed = now - timedelta(days=random.randint(60, 260))
            elif user.status == UserStatus.on_leave:
                access_count = random.randint(0, 25)
                last_accessed = now - timedelta(days=random.randint(30, 160))
            else:
                access_count = random.randint(0, 20)
                last_accessed = now - timedelta(days=random.randint(45, 180))

            db.session.add(
                AccessLog(
                    user=user,
                    system=system,
                    last_accessed=last_accessed,
                    access_count_90d=access_count,
                )
            )
    db.session.flush()


def _create_orphan_accounts(
    users: dict[str, User],
    user_active_systems: dict[str, set[str]],
    now: datetime,
) -> None:
    """Create orphan account findings for selected inactive users with active access."""

    for user_name in ORPHAN_CANDIDATES:
        user = users[user_name]
        active_systems = sorted(user_active_systems.get(user_name, set()))
        if not active_systems:
            continue

        if user.status == UserStatus.terminated and user.employment_end_date:
            days_since_termination = (now - user.employment_end_date).days
        else:
            reference_date = user.last_login or now
            days_since_termination = max((now - reference_date).days, 1)

        db.session.add(
            OrphanAccount(
                user=user,
                detected_at=now,
                days_since_termination=days_since_termination,
                systems_still_active=", ".join(active_systems),
            )
        )
    db.session.flush()


def clear_user_data() -> None:
    """Clear all user-related data while keeping systems, roles, and rules."""
    AccessLog.query.delete()
    OrphanAccount.query.delete()
    SoDViolation.query.delete()
    UserRole.query.delete()
    User.query.delete()
    db.session.commit()


def seed_custom_data(data: dict) -> None:
    """Seed the database with custom user data."""
    now = datetime.utcnow()
    roles = {r.name: r for r in Role.query.all()}
    systems = {s.name: s for s in System.query.all()}
    
    users = {}
    user_active_systems = defaultdict(set)
    
    for u_data in data.get("users", []):
        status_str = str(u_data.get("status", "active")).lower()
        if status_str == "terminated":
            status = UserStatus.terminated
        elif status_str == "on_leave":
            status = UserStatus.on_leave
        elif status_str == "suspended":
            status = UserStatus.suspended
        else:
            status = UserStatus.active
            
        last_login_days = u_data.get("last_login_days_ago", random.randint(1, 30))
        last_login = now - timedelta(days=last_login_days)
        
        user = User(
            employee_id=u_data.get("employee_id", f"EMP{random.randint(1000, 9999)}"),
            name=u_data.get("name", "Custom User"),
            email=_build_email(u_data.get("name", "Custom User")),
            department=u_data.get("department", "Custom Dept"),
            job_title=u_data.get("job_title", "Staff"),
            status=status,
            employment_end_date=now - timedelta(days=30) if status == UserStatus.terminated else None,
            last_login=last_login,
            created_at=now - timedelta(days=random.randint(100, 500)),
        )
        db.session.add(user)
        users[user.name] = user
        
        for role_name in u_data.get("roles", []):
            if role_name in roles:
                role = roles[role_name]
                is_active = (status == UserStatus.active)
                db.session.add(
                    UserRole(
                        user=user,
                        role=role,
                        assigned_date=now - timedelta(days=random.randint(45, 540)),
                        last_reviewed_date=now - timedelta(days=10) if random.random() < 0.8 else None,
                        assigned_by="Custom Upload",
                        is_active=is_active,
                    )
                )
                if is_active:
                    user_active_systems[user.name].add(role.system.name)
    
    db.session.flush()
    _create_access_logs(users, systems, user_active_systems, now)
    
    for user_name, user in users.items():
        active_systems = sorted(user_active_systems.get(user_name, set()))
        if active_systems and user.status == UserStatus.terminated:
            days_since = (now - user.employment_end_date).days if user.employment_end_date else 30
            db.session.add(
                OrphanAccount(
                    user=user,
                    detected_at=now,
                    days_since_termination=days_since,
                    systems_still_active=", ".join(active_systems),
                )
            )
    
    db.session.commit()


def seed_database(randomize: bool = False) -> None:
    """Seed the SQLite database with deterministic, idempotent IAM demo data."""

    if User.query.count() > 0:
        return

    if randomize:
        import time
        random.seed(time.time())
        # Shuffle assignments for true randomization
        all_role_lists = list(ROLE_ASSIGNMENTS.values())
        random.shuffle(all_role_lists)
        for idx, name in enumerate(ROLE_ASSIGNMENTS.keys()):
            ROLE_ASSIGNMENTS[name] = all_role_lists[idx]
    else:
        random.seed(20260508)
    now = datetime.utcnow()

    if System.query.count() == 0:
        systems = _create_systems()
        permissions = _create_permissions(systems)
        _create_sod_rules(permissions)
        roles = _create_roles(systems)
        _map_role_permissions(roles, permissions)
    else:
        systems = {s.name: s for s in System.query.all()}
        roles = {r.name: r for r in Role.query.all()}
    users = _create_users(now)
    user_active_systems = _assign_roles(users, roles, now)
    _create_access_logs(users, systems, user_active_systems, now)
    _create_orphan_accounts(users, user_active_systems, now)

    db.session.commit()




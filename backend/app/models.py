"""Phase 1 models for the IAM access review and SoD violation detector."""

from __future__ import annotations

import enum
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declarative_base, relationship


# Use SQLAlchemy declarative_base as requested for all ORM models.
Base = declarative_base()
db = SQLAlchemy(model_class=Base)


class UserStatus(str, enum.Enum):
    """Supported employee lifecycle statuses."""

    active = "active"
    terminated = "terminated"
    on_leave = "on_leave"
    suspended = "suspended"


class CriticalityLevel(str, enum.Enum):
    """System criticality levels."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskLevel(str, enum.Enum):
    """Role risk levels."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class SoDSeverity(str, enum.Enum):
    """Severity levels for SoD rules."""

    medium = "medium"
    high = "high"
    critical = "critical"


class ViolationStatus(str, enum.Enum):
    """Lifecycle states for detected SoD violations."""

    open = "open"
    remediated = "remediated"
    accepted = "accepted"


class User(db.Model):
    """Employee record for access governance and certification."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    department = db.Column(db.String(120), nullable=False)
    job_title = db.Column(db.String(120), nullable=False)
    status = db.Column(
        db.Enum(UserStatus, name="user_status", native_enum=False),
        nullable=False,
        default=UserStatus.active,
    )
    employment_end_date = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    access_logs = relationship("AccessLog", back_populates="user", cascade="all, delete-orphan")
    sod_violations = relationship("SoDViolation", back_populates="user", cascade="all, delete-orphan")
    orphan_account = relationship(
        "OrphanAccount",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary for API responses."""

        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "job_title": self.job_title,
            "status": self.status.value if self.status else None,
            "employment_end_date": self.employment_end_date.isoformat() if self.employment_end_date else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return f"<User id={self.id} employee_id={self.employee_id} status={self.status.value}>"


class System(db.Model):
    """System/application under IAM scope."""

    __tablename__ = "systems"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    criticality = db.Column(
        db.Enum(CriticalityLevel, name="criticality_level", native_enum=False),
        nullable=False,
    )
    system_type = db.Column(db.String(50), nullable=False)

    roles = relationship("Role", back_populates="system", cascade="all, delete-orphan")
    permissions = relationship("Permission", back_populates="system", cascade="all, delete-orphan")
    access_logs = relationship("AccessLog", back_populates="system", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary for API responses."""

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "criticality": self.criticality.value if self.criticality else None,
            "system_type": self.system_type,
        }

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return f"<System id={self.id} name={self.name} criticality={self.criticality.value}>"


class Role(db.Model):
    """Business or technical role that bundles permissions."""

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    risk_level = db.Column(
        db.Enum(RiskLevel, name="role_risk_level", native_enum=False),
        nullable=False,
    )
    system_id = db.Column(db.Integer, db.ForeignKey("systems.id"), nullable=False)

    system = relationship("System", back_populates="roles")
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """Return a JSON-serializable dictionary for API responses."""

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "risk_level": self.risk_level.value if self.risk_level else None,
            "system_id": self.system_id,
            "system_name": self.system.name if self.system else None,
        }

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return f"<Role id={self.id} name={self.name} risk_level={self.risk_level.value}>"


class UserRole(db.Model):
    """Assignment of a role to a user with review metadata."""

    __tablename__ = "user_roles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    assigned_date = db.Column(db.DateTime, nullable=False)
    last_reviewed_date = db.Column(db.DateTime, nullable=True)
    assigned_by = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return (
            f"<UserRole id={self.id} user_id={self.user_id} "
            f"role_id={self.role_id} is_active={self.is_active}>"
        )


class Permission(db.Model):
    """System-level permission that can be grouped into roles."""

    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    permission_type = db.Column(db.String(50), nullable=False)
    system_id = db.Column(db.Integer, db.ForeignKey("systems.id"), nullable=False)

    system = relationship("System", back_populates="permissions")
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    sod_rules_as_a = relationship(
        "SoDRule",
        foreign_keys="SoDRule.permission_a_id",
        back_populates="permission_a",
        cascade="all, delete-orphan",
    )
    sod_rules_as_b = relationship(
        "SoDRule",
        foreign_keys="SoDRule.permission_b_id",
        back_populates="permission_b",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return f"<Permission id={self.id} name={self.name} system_id={self.system_id}>"


class RolePermission(db.Model):
    """Association between roles and permissions."""

    __tablename__ = "role_permissions"

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), primary_key=True)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), primary_key=True)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return f"<RolePermission role_id={self.role_id} permission_id={self.permission_id}>"


class SoDRule(db.Model):
    """Mutually exclusive permission pair that defines an SoD conflict."""

    __tablename__ = "sod_rules"

    id = db.Column(db.Integer, primary_key=True)
    permission_a_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False)
    permission_b_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    severity = db.Column(
        db.Enum(SoDSeverity, name="sod_severity", native_enum=False),
        nullable=False,
    )
    regulatory_reference = db.Column(db.String(255), nullable=False)

    permission_a = relationship("Permission", foreign_keys=[permission_a_id], back_populates="sod_rules_as_a")
    permission_b = relationship("Permission", foreign_keys=[permission_b_id], back_populates="sod_rules_as_b")
    violations = relationship("SoDViolation", back_populates="rule", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return (
            f"<SoDRule id={self.id} permission_a_id={self.permission_a_id} "
            f"permission_b_id={self.permission_b_id} severity={self.severity.value}>"
        )


class AccessLog(db.Model):
    """Aggregated user access telemetry per system."""

    __tablename__ = "access_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    system_id = db.Column(db.Integer, db.ForeignKey("systems.id"), nullable=False)
    last_accessed = db.Column(db.DateTime, nullable=False)
    access_count_90d = db.Column(db.Integer, nullable=False)

    user = relationship("User", back_populates="access_logs")
    system = relationship("System", back_populates="access_logs")

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return (
            f"<AccessLog id={self.id} user_id={self.user_id} "
            f"system_id={self.system_id} access_count_90d={self.access_count_90d}>"
        )


class SoDViolation(db.Model):
    """Detected instance of a user violating an SoD rule."""

    __tablename__ = "sod_violations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey("sod_rules.id"), nullable=False)
    detected_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(
        db.Enum(ViolationStatus, name="violation_status", native_enum=False),
        nullable=False,
        default=ViolationStatus.open,
    )
    recommended_action = db.Column(db.String(500), nullable=False)

    user = relationship("User", back_populates="sod_violations")
    rule = relationship("SoDRule", back_populates="violations")

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return f"<SoDViolation id={self.id} user_id={self.user_id} rule_id={self.rule_id} status={self.status.value}>"


class OrphanAccount(db.Model):
    """Users with inactive employment status but active entitlements."""

    __tablename__ = "orphan_accounts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    detected_at = db.Column(db.DateTime, nullable=False)
    days_since_termination = db.Column(db.Integer, nullable=False)
    systems_still_active = db.Column(db.String(500), nullable=False)

    user = relationship("User", back_populates="orphan_account")

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return f"<OrphanAccount id={self.id} user_id={self.user_id} days_since_termination={self.days_since_termination}>"


class CertificationReport(db.Model):
    """Audit report metadata generated by access review cycles."""

    __tablename__ = "certification_reports"

    id = db.Column(db.Integer, primary_key=True)
    generated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    generated_by = db.Column(db.String(120), nullable=False)
    report_period = db.Column(db.String(80), nullable=False)
    total_users = db.Column(db.Integer, nullable=False)
    violations_found = db.Column(db.Integer, nullable=False)
    orphans_found = db.Column(db.Integer, nullable=False)
    pdf_filename = db.Column(db.String(255), nullable=False)

    def __repr__(self) -> str:
        """Return developer-friendly representation."""

        return (
            f"<CertificationReport id={self.id} report_period={self.report_period} "
            f"violations_found={self.violations_found} orphans_found={self.orphans_found}>"
        )

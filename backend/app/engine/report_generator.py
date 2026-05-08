"""PDF report generation for IAM certification aligned to RBI IT Framework and ISO 27001 Annex A.9."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import joinedload

from ..models import (
    Permission,
    Role,
    SoDRule,
    SoDViolation,
    System,
    User,
    UserRole,
    UserStatus,
    db as orm_db,
)
from . import run_full_analysis
from .orphan_detector import detect_orphan_accounts, get_orphan_summary
from .privilege_analyser import detect_over_privileged_users, detect_role_explosion
from .role_consolidator import get_rbac_health_score, suggest_role_consolidation
from .sod_detector import detect_sod_violations, get_sod_summary


DARK_BLUE = colors.HexColor("#1a3a5c")
CRITICAL_RED = colors.HexColor("#d32f2f")
HIGH_ORANGE = colors.HexColor("#f57c00")
MEDIUM_YELLOW = colors.HexColor("#fbc02d")
LIGHT_ALT = colors.HexColor("#f5f5f5")
ROW_CRITICAL = colors.HexColor("#ffebee")
ROW_HIGH = colors.HexColor("#fff3e0")
ROW_MEDIUM = colors.HexColor("#fffde7")


class NumberedConfidentialCanvas(Canvas):
    """Canvas that applies footer page numbering after total page count is known."""

    def __init__(self, *args, **kwargs):
        """Initialize page state tracking for deferred footer rendering."""

        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        """Capture page state instead of finalizing immediately."""

        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        """Render page numbers and confidentiality footer on all pages, then save."""

        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(total_pages)
            Canvas.showPage(self)
        Canvas.save(self)

    def _draw_footer(self, total_pages: int) -> None:
        """Draw the required footer text on each page."""

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.black)
        footer_text = (
            f"Page {self._pageNumber} of {total_pages} | CONFIDENTIAL | Bank"
        )
        self.drawCentredString(letter[0] / 2, 0.5 * inch, footer_text)
        self.restoreState()


def _quarter_label(timestamp: datetime) -> str:
    """Return quarter label in the required `Q{n} YYYY` format."""

    quarter = ((timestamp.month - 1) // 3) + 1
    return f"Q{quarter} {timestamp.year}"


def _build_styles() -> dict[str, ParagraphStyle]:
    """Create centralized paragraph styles for consistent report typography."""

    sample_styles = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {
        "cover_title": ParagraphStyle(
            "cover_title",
            parent=sample_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=DARK_BLUE,
            alignment=1,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            parent=sample_styles["Heading2"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=colors.black,
            alignment=1,
            spaceAfter=12,
        ),
        "body": ParagraphStyle(
            "body",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            spaceAfter=6,
        ),
        "section": ParagraphStyle(
            "section",
            parent=sample_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=DARK_BLUE,
            spaceAfter=4,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=sample_styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white,
            alignment=1,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        ),
        "table_cell_center": ParagraphStyle(
            "table_cell_center",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=4,
        ),
    }
    return styles


def _section_header(title: str, styles: dict[str, ParagraphStyle], doc_width: float) -> KeepTogether:
    """Return section header block with a dark-blue underline rule."""

    underline = Table([[""]], colWidths=[doc_width], rowHeights=[2])
    underline.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, 0), 2, DARK_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return KeepTogether(
        [
            Paragraph(title, styles["section"]),
            Spacer(1, 0.04 * inch),
            underline,
            Spacer(1, 0.14 * inch),
        ]
    )


def _base_table_style() -> TableStyle:
    """Return reusable table style with required header theme and grid lines."""

    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9e9e9e")),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _cover_canvas(canvas: Canvas, _doc) -> None:
    """Draw cover-specific visual elements: top bar and rotated watermark."""

    canvas.saveState()
    canvas.setFillColor(DARK_BLUE)
    canvas.rect(0, letter[1] - (1.2 * inch), letter[0], 1.2 * inch, stroke=0, fill=1)

    canvas.setFont("Helvetica-Bold", 56)
    canvas.setFillColor(colors.HexColor("#d6dce3"))
    canvas.translate(letter[0] / 2, letter[1] / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "CONFIDENTIAL")
    canvas.restoreState()


def _later_canvas(_canvas: Canvas, _doc) -> None:
    """Reserved hook for later-page custom drawing."""

    return None


def _health_color(score: int) -> colors.Color:
    """Return score color according to requested health thresholds."""

    if score >= 70:
        return colors.HexColor("#2e7d32")
    if score >= 40:
        return HIGH_ORANGE
    return CRITICAL_RED


def _status_to_text(status_key: str) -> str:
    """Map internal compliance status keys to requested checklist labels."""

    if status_key == "compliant":
        return "✓ Compliant"
    if status_key == "non_compliant":
        return "✗ Non-Compliant"
    return "⚠ Partial"


def _status_to_color(status_key: str) -> colors.Color:
    """Map checklist status key to display color."""

    if status_key == "compliant":
        return colors.HexColor("#2e7d32")
    if status_key == "non_compliant":
        return CRITICAL_RED
    return HIGH_ORANGE


def _to_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    """Safely build a paragraph with explicit text conversion."""

    return Paragraph(str(text), style)


def generate_pdf_report(db=orm_db) -> bytes:
    """
    Generates a complete IAM Access Certification Report in PDF format.

    Compliant with:
    - RBI IT Framework for Banks (2011, amended 2023): §3.2 Segregation of Duties,
      §5.1 User Access Management
    - ISO 27001:2022 Annex A.9: Access Control

    Returns:
        bytes: PDF file content suitable for HTTP streaming response
    """

    now = datetime.utcnow()
    report_period = _quarter_label(now)

    analysis = run_full_analysis(db)
    sod_violations = detect_sod_violations(db)
    sod_summary = get_sod_summary(db)
    orphan_accounts = detect_orphan_accounts(db)
    orphan_summary = get_orphan_summary(db)
    over_privileged_users = detect_over_privileged_users(db)
    role_explosion = detect_role_explosion(db)
    consolidation_suggestions = suggest_role_consolidation(db)
    health_score = get_rbac_health_score(db)

    session = db.session
    total_users = session.query(User).count()
    active_users = session.query(User).filter(User.status == UserStatus.active).count()

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title="IAM Access Certification Report",
        author="IAM Compliance Engine v1.0",
    )
    styles = _build_styles()
    story: list[Any] = []

    # 1) Cover page
    story.append(Spacer(1, 1.45 * inch))
    story.append(Paragraph("IAM Access Certification Report", styles["cover_title"]))
    story.append(
        Paragraph("Segregation of Duties &amp; Access Rights Review", styles["cover_subtitle"])
    )
    story.append(Spacer(1, 0.25 * inch))
    story.append(_to_paragraph("Bank", styles["body"]))
    story.append(_to_paragraph(f"Report Period: {report_period}", styles["body"]))
    story.append(
        _to_paragraph(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}", styles["body"])
    )
    story.append(_to_paragraph("Generated by: IAM Compliance Engine v1.0", styles["body"]))
    story.append(
        _to_paragraph(
            f"Analysis Timestamp: {analysis.get('analysis_timestamp', now.isoformat())}",
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.35 * inch))
    story.append(
        _to_paragraph(
            (
                "Prepared per RBI IT Framework for Banks (2011, amended 2023) and "
                "ISO 27001:2022 Annex A.9 - Access Control"
            ),
            styles["body"],
        )
    )
    story.append(PageBreak())

    # 2) Executive summary
    story.append(_section_header("Executive Summary", styles, document.width))

    summary_headers = [
        _to_paragraph("Total Users", styles["table_header"]),
        _to_paragraph("SoD Violations", styles["table_header"]),
        _to_paragraph("Orphan Accounts", styles["table_header"]),
        _to_paragraph("Health Score", styles["table_header"]),
    ]
    summary_values = [
        _to_paragraph(str(total_users), styles["table_cell_center"]),
        _to_paragraph(str(sod_summary["total_violations"]), styles["table_cell_center"]),
        _to_paragraph(str(orphan_summary["total_orphan_accounts"]), styles["table_cell_center"]),
        _to_paragraph(str(health_score), styles["table_cell_center"]),
    ]
    summary_table = Table(
        [summary_headers, summary_values],
        colWidths=[document.width / 4.0] * 4,
        repeatRows=1,
    )
    summary_style = _base_table_style()
    sod_metric_color = (
        CRITICAL_RED
        if sod_summary["critical"] > 0
        else HIGH_ORANGE if sod_summary["high"] > 0 else colors.HexColor("#2e7d32")
    )
    orphan_metric_color = (
        CRITICAL_RED
        if orphan_summary["critical"] > 0
        else HIGH_ORANGE if orphan_summary["high"] > 0 else colors.HexColor("#2e7d32")
    )
    summary_style.add("TEXTCOLOR", (1, 1), (1, 1), sod_metric_color)
    summary_style.add(
        "TEXTCOLOR",
        (2, 1),
        (2, 1),
        orphan_metric_color,
    )
    summary_style.add("TEXTCOLOR", (3, 1), (3, 1), _health_color(health_score))
    summary_table.setStyle(summary_style)
    story.append(summary_table)
    story.append(Spacer(1, 0.2 * inch))

    key_findings = []
    if sod_summary["critical"] > 0:
        key_findings.append(
            (
                f"{sod_summary['critical']} critical SoD conflicts are open and require immediate "
                "remediation under RBI IT Framework §3.2."
            )
        )
    if orphan_summary["total_orphan_accounts"] > 0:
        key_findings.append(
            (
                f"{orphan_summary['total_orphan_accounts']} orphan accounts remain active, creating "
                "post-termination exposure under RBI IT Framework §5.1."
            )
        )
    if len(over_privileged_users) > 0:
        key_findings.append(
            (
                f"{len(over_privileged_users)} users hold excessive or dormant privileges requiring "
                "least-privilege recertification."
            )
        )
    if role_explosion["role_explosion_score"] != "none":
        key_findings.append(
            (
                "Role-set entropy indicates RBAC sprawl; consolidation opportunities should be "
                "prioritized for governance efficiency."
            )
        )
    if not key_findings:
        key_findings.append(
            "No major compliance findings were identified during this review cycle."
        )

    story.append(_to_paragraph("Key Findings:", styles["body"]))
    for finding in key_findings:
        story.append(_to_paragraph(f"• {finding}", styles["bullet"]))

    story.append(
        _to_paragraph(
            (
                "These findings directly support RBI IT Framework control objectives around maker-"
                "checker segregation, revocation of stale entitlements, and periodic recertification "
                "of privileged access."
            ),
            styles["body"],
        )
    )
    story.append(PageBreak())

    # 3) SoD violations table
    story.append(_section_header("Segregation of Duties Violations", styles, document.width))
    story.append(
        _to_paragraph(
            (
                "Per RBI IT Framework §3.2 and ISO 27001:2022 Annex A.9.4.1, no single individual "
                "should possess conflicting access rights that could enable unauthorized or "
                "fraudulent transactions."
            ),
            styles["body"],
        )
    )

    role_map = {(item["user_id"], item["rule_id"]): item for item in sod_violations}
    sod_records = (
        session.query(SoDViolation)
        .options(
            joinedload(SoDViolation.user),
            joinedload(SoDViolation.rule)
            .joinedload(SoDRule.permission_a)
            .joinedload(Permission.system),
            joinedload(SoDViolation.rule)
            .joinedload(SoDRule.permission_b)
            .joinedload(Permission.system),
        )
        .order_by(SoDViolation.detected_at.desc(), SoDViolation.id.desc())
        .all()
    )

    sod_rows: list[list[Any]] = [
        [
            _to_paragraph("#", styles["table_header"]),
            _to_paragraph("Employee", styles["table_header"]),
            _to_paragraph("Department", styles["table_header"]),
            _to_paragraph("System", styles["table_header"]),
            _to_paragraph("Conflicting Roles", styles["table_header"]),
            _to_paragraph("Severity", styles["table_header"]),
            _to_paragraph("Regulatory Ref", styles["table_header"]),
            _to_paragraph("Recommended Action", styles["table_header"]),
        ]
    ]

    if not sod_records:
        sod_rows.append(
            [
                "1",
                "No violations found",
                "-",
                "-",
                "-",
                "-",
                "-",
                "No remediation needed.",
            ]
        )
    else:
        for idx, record in enumerate(sod_records, start=1):
            details = role_map.get((record.user_id, record.rule_id), {})
            rule = record.rule
            system_names = []
            if rule and rule.permission_a and rule.permission_a.system:
                system_names.append(rule.permission_a.system.name)
            if rule and rule.permission_b and rule.permission_b.system:
                system_names.append(rule.permission_b.system.name)
            unique_systems = sorted(set(system_names))
            system_label = ", ".join(unique_systems) if unique_systems else "Unknown"
            conflicting_roles = ", ".join(
                value
                for value in [details.get("role_a_name"), details.get("role_b_name")]
                if value
            )
            if not conflicting_roles:
                conflicting_roles = "Role mapping unavailable"

            sod_rows.append(
                [
                    str(idx),
                    _to_paragraph(record.user.name if record.user else "-", styles["table_cell"]),
                    _to_paragraph(record.user.department if record.user else "-", styles["table_cell"]),
                    _to_paragraph(system_label, styles["table_cell"]),
                    _to_paragraph(conflicting_roles, styles["table_cell"]),
                    _to_paragraph(rule.severity.value if rule and rule.severity else "-", styles["table_cell_center"]),
                    _to_paragraph(rule.regulatory_reference if rule else "-", styles["table_cell"]),
                    _to_paragraph(record.recommended_action, styles["table_cell"]),
                ]
            )

    sod_table = Table(
        sod_rows,
        colWidths=[0.3 * inch, 0.85 * inch, 0.75 * inch, 0.75 * inch, 0.9 * inch, 0.5 * inch, 0.8 * inch, 1.65 * inch],
        repeatRows=1,
    )
    sod_style = _base_table_style()
    for row_index, row in enumerate(sod_rows[1:], start=1):
        if not sod_records:
            sod_style.add("BACKGROUND", (0, row_index), (-1, row_index), LIGHT_ALT)
            continue
        severity_text = str(row[5].text).lower() if hasattr(row[5], "text") else str(row[5]).lower()
        if "critical" in severity_text:
            sod_style.add("BACKGROUND", (0, row_index), (-1, row_index), ROW_CRITICAL)
        elif "high" in severity_text:
            sod_style.add("BACKGROUND", (0, row_index), (-1, row_index), ROW_HIGH)
        else:
            sod_style.add("BACKGROUND", (0, row_index), (-1, row_index), ROW_MEDIUM)
    sod_table.setStyle(sod_style)
    story.append(sod_table)

    open_count = sum(1 for record in sod_records if record.status and record.status.value == "open")
    remediated_count = sum(
        1 for record in sod_records if record.status and record.status.value == "remediated"
    )
    accepted_count = sum(
        1 for record in sod_records if record.status and record.status.value == "accepted"
    )
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        _to_paragraph(
            (
                f"Violation Status Summary: Open = {open_count}, Remediated = {remediated_count}, "
                f"Accepted Risk = {accepted_count}"
            ),
            styles["body"],
        )
    )
    story.append(PageBreak())

    # 4) Orphan accounts table
    story.append(_section_header("Orphan Account Analysis", styles, document.width))
    story.append(
        _to_paragraph(
            (
                "Per RBI IT Framework §5.1 and ISO 27001:2022 Annex A.9.2.6, access rights of all "
                "employees shall be removed upon termination."
            ),
            styles["body"],
        )
    )

    orphan_rows: list[list[Any]] = [
        [
            _to_paragraph("Employee ID", styles["table_header"]),
            _to_paragraph("Name", styles["table_header"]),
            _to_paragraph("Dept", styles["table_header"]),
            _to_paragraph("Status", styles["table_header"]),
            _to_paragraph("Days Since Termination", styles["table_header"]),
            _to_paragraph("Active Systems", styles["table_header"]),
            _to_paragraph("Risk", styles["table_header"]),
            _to_paragraph("Recommended Action", styles["table_header"]),
        ]
    ]
    orphan_sorted = sorted(orphan_accounts, key=lambda item: item["days_since_termination"], reverse=True)
    if not orphan_sorted:
        orphan_rows.append(
            ["-", "No orphan accounts found", "-", "-", "0", "-", "-", "No action required."]
        )
    else:
        for item in orphan_sorted:
            orphan_rows.append(
                [
                    _to_paragraph(item["employee_id"], styles["table_cell"]),
                    _to_paragraph(item["user_name"], styles["table_cell"]),
                    _to_paragraph(item["department"], styles["table_cell"]),
                    _to_paragraph(item["user_status"], styles["table_cell_center"]),
                    _to_paragraph(str(item["days_since_termination"]), styles["table_cell_center"]),
                    _to_paragraph(", ".join(item["active_systems"]), styles["table_cell"]),
                    _to_paragraph(item["risk_level"], styles["table_cell_center"]),
                    _to_paragraph(item["recommended_action"], styles["table_cell"]),
                ]
            )

    orphan_table = Table(
        orphan_rows,
        colWidths=[0.65 * inch, 0.8 * inch, 0.6 * inch, 0.5 * inch, 0.65 * inch, 1.2 * inch, 0.4 * inch, 1.7 * inch],
        repeatRows=1,
    )
    orphan_style = _base_table_style()
    for row_index, item in enumerate(orphan_sorted, start=1):
        days = item["days_since_termination"]
        if days > 90:
            orphan_style.add("BACKGROUND", (0, row_index), (-1, row_index), ROW_CRITICAL)
        elif days > 30:
            orphan_style.add("BACKGROUND", (0, row_index), (-1, row_index), ROW_HIGH)
        else:
            orphan_style.add("BACKGROUND", (0, row_index), (-1, row_index), ROW_MEDIUM)
    if not orphan_sorted:
        orphan_style.add("BACKGROUND", (0, 1), (-1, 1), LIGHT_ALT)
    orphan_table.setStyle(orphan_style)
    story.append(orphan_table)
    story.append(PageBreak())

    # 5) Over-privileged users
    story.append(_section_header("Excessive Privilege Analysis", styles, document.width))
    story.append(
        _to_paragraph(
            (
                "Per ISO 27001:2022 Annex A.9.2.3 (management of privileged access rights), "
                "privileged access rights shall be allocated on a need-to-use basis."
            ),
            styles["body"],
        )
    )

    over_rows: list[list[Any]] = [
        [
            _to_paragraph("Employee", styles["table_header"]),
            _to_paragraph("Dept", styles["table_header"]),
            _to_paragraph("Total Roles", styles["table_header"]),
            _to_paragraph("Unused Admin Roles", styles["table_header"]),
            _to_paragraph("Systems Inactive 90d", styles["table_header"]),
            _to_paragraph("Risk Score", styles["table_header"]),
            _to_paragraph("Action", styles["table_header"]),
        ]
    ]
    if not over_privileged_users:
        over_rows.append(["-", "-", "0", "-", "-", "-", "No over-privileged users found."])
    else:
        for item in over_privileged_users:
            over_rows.append(
                [
                    _to_paragraph(item["user_name"], styles["table_cell"]),
                    _to_paragraph(item["department"], styles["table_cell"]),
                    _to_paragraph(str(item["total_active_roles"]), styles["table_cell_center"]),
                    _to_paragraph(", ".join(item["unused_admin_roles"]) or "-", styles["table_cell"]),
                    _to_paragraph(
                        ", ".join(item["systems_not_accessed_90d"]) or "-", styles["table_cell"]
                    ),
                    _to_paragraph(str(item["risk_score"]), styles["table_cell_center"]),
                    _to_paragraph(item["recommended_action"], styles["table_cell"]),
                ]
            )

    over_table = Table(
        over_rows,
        colWidths=[0.9 * inch, 0.7 * inch, 0.45 * inch, 1.1 * inch, 1.1 * inch, 0.45 * inch, 1.8 * inch],
        repeatRows=1,
    )
    over_style = _base_table_style()
    over_style.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_ALT])
    over_table.setStyle(over_style)
    story.append(over_table)
    story.append(PageBreak())

    # 6) Role consolidation recommendations
    story.append(_section_header("RBAC Optimisation Recommendations", styles, document.width))
    story.append(
        _to_paragraph(
            (
                "The following role pairs have >=60% permission overlap, indicating opportunities "
                "for consolidation that would reduce the attack surface and simplify future access "
                "reviews per ISO 27001:2022 Annex A.9.1.2."
            ),
            styles["body"],
        )
    )

    consolidation_rows: list[list[Any]] = [
        [
            _to_paragraph("Role A", styles["table_header"]),
            _to_paragraph("Role B", styles["table_header"]),
            _to_paragraph("Similarity %", styles["table_header"]),
            _to_paragraph("Shared Permissions", styles["table_header"]),
            _to_paragraph("Users Affected", styles["table_header"]),
            _to_paragraph("Action", styles["table_header"]),
        ]
    ]
    if not consolidation_suggestions:
        consolidation_rows.append(["-", "-", "0%", "-", "0", "No consolidation candidates found."])
    else:
        for item in consolidation_suggestions:
            similarity_pct = int(round(float(item["similarity_score"]) * 100))
            consolidation_rows.append(
                [
                    _to_paragraph(item["role_a_name"], styles["table_cell"]),
                    _to_paragraph(item["role_b_name"], styles["table_cell"]),
                    _to_paragraph(f"{similarity_pct}%", styles["table_cell_center"]),
                    _to_paragraph(", ".join(item["shared_permissions"]), styles["table_cell"]),
                    _to_paragraph(item["estimated_impact"], styles["table_cell"]),
                    _to_paragraph(item["consolidation_recommendation"], styles["table_cell"]),
                ]
            )

    consolidation_table = Table(
        consolidation_rows,
        colWidths=[0.85 * inch, 0.85 * inch, 0.55 * inch, 1.2 * inch, 0.9 * inch, 2.15 * inch],
        repeatRows=1,
    )
    consolidation_style = _base_table_style()
    consolidation_style.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_ALT])
    consolidation_table.setStyle(consolidation_style)
    story.append(consolidation_table)
    story.append(PageBreak())

    # 7) Compliance checklist
    story.append(_section_header("Compliance Checklist", styles, document.width))

    sod_control = "non_compliant" if sod_summary["critical"] > 0 else "partial" if sod_summary["total_violations"] > 0 else "compliant"
    orphan_control = "non_compliant" if orphan_summary["total_orphan_accounts"] > 0 else "compliant"
    privileged_control = "non_compliant" if len(over_privileged_users) > 2 else "partial" if over_privileged_users else "compliant"
    periodic_review_control = "partial" if role_explosion["role_explosion_score"] in {"moderate", "severe"} else "compliant"
    termination_control = "non_compliant" if orphan_summary["critical"] > 0 else "partial" if orphan_summary["total_orphan_accounts"] > 0 else "compliant"

    privileged_utility_control = "compliant"
    for item in sod_violations:
        permission_a = str(item.get("permission_a", "")).lower()
        permission_b = str(item.get("permission_b", "")).lower()
        if "admin" in permission_a or "admin" in permission_b:
            privileged_utility_control = "non_compliant" if item.get("severity") == "critical" else "partial"
            break

    checklist_items = [
        ("RBI IT Framework §3.2: Segregation of Duties enforced", sod_control),
        ("RBI IT Framework §5.1: Terminated user access revoked", orphan_control),
        ("ISO 27001 A.9.2.3: Privileged access reviewed", privileged_control),
        ("ISO 27001 A.9.2.5: Access rights reviewed periodically", periodic_review_control),
        ("ISO 27001 A.9.2.6: Access rights removed on termination", termination_control),
        ("ISO 27001 A.9.4.1: Use of privileged utility programs restricted", privileged_utility_control),
    ]

    checklist_rows = [
        [
            _to_paragraph("Control", styles["table_header"]),
            _to_paragraph("Status", styles["table_header"]),
        ]
    ]
    for control_name, status_key in checklist_items:
        checklist_rows.append(
            [
                _to_paragraph(control_name, styles["table_cell"]),
                _to_paragraph(_status_to_text(status_key), styles["table_cell_center"]),
            ]
        )

    checklist_table = Table(
        checklist_rows,
        colWidths=[4.8 * inch, 1.7 * inch],
        repeatRows=1,
    )
    checklist_style = _base_table_style()
    checklist_style.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_ALT])
    for row_index, (_, status_key) in enumerate(checklist_items, start=1):
        checklist_style.add("TEXTCOLOR", (1, row_index), (1, row_index), _status_to_color(status_key))
    checklist_table.setStyle(checklist_style)
    story.append(checklist_table)
    story.append(PageBreak())

    # 8) Appendix user-role matrix
    story.append(_section_header("Appendix: User-Role Matrix", styles, document.width))

    systems = session.query(System).order_by(System.name.asc()).all()
    system_names = [system.name for system in systems]

    active_users_data = (
        session.query(User)
        .options(joinedload(User.user_roles).joinedload(UserRole.role).joinedload(Role.system))
        .filter(User.status == UserStatus.active)
        .order_by(User.name.asc())
        .all()
    )

    if len(active_users_data) > 20:
        violated_user_ids = {item["user_id"] for item in sod_violations}
        admin_user_ids = set()
        for user in active_users_data:
            for assignment in user.user_roles:
                if not assignment.is_active or not assignment.role:
                    continue
                if "admin" in assignment.role.name.lower():
                    admin_user_ids.add(user.id)
                    break
        appendix_users = [
            user
            for user in active_users_data
            if user.id in violated_user_ids or user.id in admin_user_ids
        ]
    else:
        appendix_users = active_users_data

    matrix_header = [
        _to_paragraph("Emp ID", styles["table_header"]),
        _to_paragraph("Name", styles["table_header"]),
        _to_paragraph("Dept", styles["table_header"]),
    ] + [_to_paragraph(system_name, styles["table_header"]) for system_name in system_names]
    matrix_rows: list[list[Any]] = [matrix_header]

    if not appendix_users:
        matrix_rows.append(
            [
                "N/A",
                "No active users for matrix",
                "-",
            ]
            + ["-"] * len(system_names)
        )
    else:
        for user in appendix_users:
            assigned_systems = {
                assignment.role.system.name
                for assignment in user.user_roles
                if assignment.is_active and assignment.role and assignment.role.system
            }
            row = [
                _to_paragraph(user.employee_id, styles["table_cell"]),
                _to_paragraph(user.name, styles["table_cell"]),
                _to_paragraph(user.department, styles["table_cell"]),
            ]
            for system_name in system_names:
                mark = "Y" if system_name in assigned_systems else "N"
                row.append(_to_paragraph(mark, styles["table_cell_center"]))
            matrix_rows.append(row)

    matrix_col_widths = [0.7 * inch, 1.1 * inch, 0.9 * inch]
    if system_names:
        remaining_width = document.width - sum(matrix_col_widths)
        per_system = max(0.45 * inch, remaining_width / len(system_names))
        matrix_col_widths.extend([per_system] * len(system_names))

    matrix_table = Table(matrix_rows, colWidths=matrix_col_widths, repeatRows=1)
    matrix_style = _base_table_style()
    matrix_style.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_ALT])
    for row_index in range(1, len(matrix_rows)):
        for col_index in range(3, len(matrix_rows[row_index])):
            value = matrix_rows[row_index][col_index]
            if hasattr(value, "text") and value.text == "Y":
                matrix_style.add("TEXTCOLOR", (col_index, row_index), (col_index, row_index), colors.HexColor("#1b5e20"))
    matrix_table.setStyle(matrix_style)

    appendix_note = (
        "Appendix filtered to active users with violations or admin roles because total active "
        f"population is {active_users} (>20)."
        if len(active_users_data) > 20
        else "Appendix includes all active users."
    )
    story.append(_to_paragraph(appendix_note, styles["body"]))
    story.append(matrix_table)

    document.build(
        story,
        onFirstPage=_cover_canvas,
        onLaterPages=_later_canvas,
        canvasmaker=NumberedConfidentialCanvas,
    )
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

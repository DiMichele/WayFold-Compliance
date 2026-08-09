from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .checklist import build_unified_checklist
from .dates import is_overdue, parse_date
from .domain import ProgramSnapshot, UnifiedChecklist


class GapTaxonomy:
    IMPLEMENTATION = "IMPLEMENTATION"
    PARTIAL_COVERAGE = "PARTIAL_COVERAGE"
    UNMAPPED = "UNMAPPED"
    EVIDENCE = "EVIDENCE"
    REMEDIATION = "REMEDIATION"


GAP_TAXONOMY_IT = {
    GapTaxonomy.IMPLEMENTATION: "Implementazione",
    GapTaxonomy.PARTIAL_COVERAGE: "Copertura parziale",
    GapTaxonomy.UNMAPPED: "Non mappato",
    GapTaxonomy.EVIDENCE: "Evidenza",
    GapTaxonomy.REMEDIATION: "Remediation",
}


@dataclass
class GapRow:
    framework_id: str
    framework_name: str
    framework_version: str
    requirement_id: str
    requirement_code: str
    requirement_title: str
    canonical_control_ref: str | None
    control_name: str | None
    mapping: str  # FULL|PARTIAL|SUPPORTING|UNMAPPED
    status: str
    owner: str | None
    deadline: str | None
    priority: str | None
    evidence_count: int
    open_task_count: int
    gap: str
    notes: str
    mapped: bool
    taxonomy: str = GapTaxonomy.IMPLEMENTATION
    severity: str = "MEDIUM"


@dataclass
class GapFilter:
    framework: str | None = None
    status: str | None = None
    owner: str | None = None
    priority: str | None = None
    deadline_before: str | None = None
    deadline_after: str | None = None
    mapped: bool | None = None  # True=mapped only, False=unmapped only
    missing_evidence: bool | None = None
    search: str | None = None


def build_gap_rows(
    program: ProgramSnapshot, checklist: UnifiedChecklist | None = None
) -> list[GapRow]:
    checklist = checklist or build_unified_checklist(program)
    req_title = {r.id: r.title for r in program.requirements}
    rows: list[GapRow] = []

    for ctrl in checklist.controls:
        for cov in ctrl.framework_coverage:
            taxonomy = GapTaxonomy.IMPLEMENTATION
            if cov.relation.value == "PARTIAL" and cov.uncovered_delta:
                taxonomy = GapTaxonomy.PARTIAL_COVERAGE
            elif ctrl.evidence_count == 0 and ctrl.status.value != "NOT_APPLICABLE":
                taxonomy = GapTaxonomy.EVIDENCE
            elif ctrl.open_task_count > 0 and is_overdue(ctrl.due_date):
                taxonomy = GapTaxonomy.REMEDIATION
            sev = (ctrl.priority or "MEDIUM").upper()
            rows.append(
                GapRow(
                    framework_id=cov.framework_id,
                    framework_name=cov.framework_name,
                    framework_version=cov.framework_version,
                    requirement_id=cov.requirement_id,
                    requirement_code=cov.requirement_code,
                    requirement_title=req_title.get(cov.requirement_id, ""),
                    canonical_control_ref=ctrl.canonical_control_ref,
                    control_name=ctrl.name,
                    mapping=cov.relation.value,
                    status=ctrl.status.value,
                    owner=ctrl.owner,
                    deadline=ctrl.due_date,
                    priority=ctrl.priority,
                    evidence_count=ctrl.evidence_count,
                    open_task_count=ctrl.open_task_count,
                    gap=cov.uncovered_delta or ctrl.gap_notes,
                    notes=cov.rationale,
                    mapped=True,
                    taxonomy=taxonomy,
                    severity=sev,
                )
            )

    for u in checklist.unmapped:
        rows.append(
            GapRow(
                framework_id=u.framework_id,
                framework_name=u.framework_name,
                framework_version=u.framework_version,
                requirement_id=u.requirement_id,
                requirement_code=u.code,
                requirement_title=u.title,
                canonical_control_ref=None,
                control_name=None,
                mapping="UNMAPPED",
                status="UNMAPPED",
                owner=None,
                deadline=None,
                priority=None,
                evidence_count=0,
                open_task_count=0,
                gap="Nessuna mappatura approvata a un controllo canonico",
                notes="",
                mapped=False,
                taxonomy=GapTaxonomy.UNMAPPED,
                severity="HIGH",
            )
        )

    rows.sort(
        key=lambda r: (
            r.framework_name,
            r.requirement_code,
            r.canonical_control_ref or "",
        )
    )
    return rows


def filter_gap_rows(rows: list[GapRow], flt: GapFilter) -> list[GapRow]:
    out = rows
    if flt.framework:
        key = flt.framework.lower()
        out = [
            r
            for r in out
            if key in r.framework_name.lower() or key == r.framework_id.lower()
        ]
    if flt.status:
        st = flt.status.upper()
        out = [r for r in out if r.status.upper() == st]
    if flt.owner:
        own = flt.owner.lower()
        out = [r for r in out if (r.owner or "").lower().find(own) >= 0]
    if flt.priority:
        pr = flt.priority.upper()
        out = [r for r in out if (r.priority or "").upper() == pr]
    if flt.mapped is True:
        out = [r for r in out if r.mapped]
    elif flt.mapped is False:
        out = [r for r in out if not r.mapped]
    if flt.missing_evidence is True:
        out = [r for r in out if r.mapped and r.evidence_count <= 0]
    if flt.deadline_before:
        before = parse_date(flt.deadline_before)
        if before:
            out = [
                r
                for r in out
                if (d := parse_date(r.deadline)) is not None and d <= before
            ]
    if flt.deadline_after:
        after = parse_date(flt.deadline_after)
        if after:
            out = [
                r
                for r in out
                if (d := parse_date(r.deadline)) is not None and d >= after
            ]
    if flt.search:
        q = flt.search.lower()
        out = [
            r
            for r in out
            if q in (r.requirement_code or "").lower()
            or q in (r.requirement_title or "").lower()
            or q in (r.canonical_control_ref or "").lower()
            or q in (r.control_name or "").lower()
            or q in (r.gap or "").lower()
            or q in (r.mapping or "").lower()
            or q in (r.notes or "").lower()
        ]
    return out


def overdue_gap_rows(rows: list[GapRow], *, as_of: date | None = None) -> list[GapRow]:
    return [r for r in rows if is_overdue(r.deadline, as_of=as_of)]

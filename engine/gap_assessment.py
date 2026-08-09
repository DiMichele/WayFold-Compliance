"""Gap / finding engine.

Findings are emitted ONLY when a real problem exists.
Never one row per coverage. Never leak PARTIAL delta across requirements
that share a canonical control.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .checklist import build_unified_checklist
from .dates import is_overdue, parse_date
from .domain import (
    ImplementationStatus,
    ProgramSnapshot,
    UnifiedChecklist,
)


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
    mapping: str  # FULL|PARTIAL|SUPPORTING|UNMAPPED|NEEDS_REVIEW
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
    mapped: bool | None = None
    missing_evidence: bool | None = None
    search: str | None = None
    taxonomy: str | None = None


@dataclass
class GapCounters:
    requirements_with_problems: int
    findings_total: int


def build_gap_rows(
    program: ProgramSnapshot, checklist: UnifiedChecklist | None = None
) -> list[GapRow]:
    checklist = checklist or build_unified_checklist(program)
    req_title = {r.id: r.title for r in program.requirements}
    rows: list[GapRow] = []

    # Index open/overdue tasks by control_ref for REMEDIATION findings
    open_tasks_by_ctrl: dict[str, list] = {}
    for t in program.tasks or []:
        st = (t.status or "").upper()
        if st in {"DONE", "COMPLETED", "CLOSED"}:
            continue
        ref = t.control_ref or ""
        open_tasks_by_ctrl.setdefault(ref, []).append(t)

    for ctrl in checklist.controls:
        status = ctrl.status
        for cov in ctrl.framework_coverage:
            # PARTIAL_COVERAGE — only this coverage's uncovered_delta (no ctrl.gap_notes leak)
            if cov.relation.value == "PARTIAL" and (cov.uncovered_delta or "").strip():
                rows.append(
                    _row(
                        cov=cov,
                        ctrl=ctrl,
                        req_title=req_title,
                        taxonomy=GapTaxonomy.PARTIAL_COVERAGE,
                        gap=cov.uncovered_delta.strip(),
                        mapped=True,
                        severity="HIGH",
                    )
                )

            # NEEDS_REVIEW core link without approved mapping
            if cov.relation.value == "NEEDS_REVIEW":
                rows.append(
                    _row(
                        cov=cov,
                        ctrl=ctrl,
                        req_title=req_title,
                        taxonomy=GapTaxonomy.UNMAPPED,
                        gap="Collegamento core senza mappatura WayFold approvata",
                        mapped=False,
                        severity="HIGH",
                    )
                )

        # IMPLEMENTATION — once per control when status requires remediation
        if status in {
            ImplementationStatus.NOT_IMPLEMENTED,
            ImplementationStatus.IN_PROGRESS,
        }:
            # Attach to primary coverage if any, else synthetic
            cov = ctrl.framework_coverage[0] if ctrl.framework_coverage else None
            if cov is not None:
                rows.append(
                    _row(
                        cov=cov,
                        ctrl=ctrl,
                        req_title=req_title,
                        taxonomy=GapTaxonomy.IMPLEMENTATION,
                        gap=f"Stato implementazione: {status.value}",
                        mapped=True,
                        severity=(ctrl.priority or "MEDIUM").upper(),
                    )
                )

        # EVIDENCE — when evidence is actually missing for a non-N/A control
        if (
            ctrl.evidence_count == 0
            and status != ImplementationStatus.NOT_APPLICABLE
            and ctrl.framework_coverage
        ):
            cov = ctrl.framework_coverage[0]
            rows.append(
                _row(
                    cov=cov,
                    ctrl=ctrl,
                    req_title=req_title,
                    taxonomy=GapTaxonomy.EVIDENCE,
                    gap="Evidenza richiesta mancante",
                    mapped=True,
                    severity="MEDIUM",
                )
            )

        # REMEDIATION — specific open/overdue tasks linked to this control
        refs = {
            x
            for x in (ctrl.canonical_control_ref, ctrl.implementation_id)
            if x
        }
        for ref in refs:
            for t in open_tasks_by_ctrl.get(ref, []):
                st = (t.status or "").upper()
                if st in {"DONE", "COMPLETED", "CLOSED"}:
                    continue
                if not (is_overdue(t.due_date) or st in {"TODO", "IN_PROGRESS", "OPEN", "REVIEW"}):
                    continue
                cov = ctrl.framework_coverage[0] if ctrl.framework_coverage else None
                if cov is None:
                    continue
                note = f"Task aperta: {t.title}"
                if is_overdue(t.due_date):
                    note += " (scaduta)"
                rows.append(
                    _row(
                        cov=cov,
                        ctrl=ctrl,
                        req_title=req_title,
                        taxonomy=GapTaxonomy.REMEDIATION,
                        gap=note,
                        mapped=True,
                        severity=(t.priority or ctrl.priority or "MEDIUM").upper(),
                        owner=t.owner or ctrl.owner,
                        deadline=t.due_date or ctrl.due_date,
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
            r.taxonomy,
            r.canonical_control_ref or "",
        )
    )
    return rows


def gap_counters(rows: list[GapRow]) -> GapCounters:
    req_ids = {r.requirement_id for r in rows if r.requirement_id}
    return GapCounters(
        requirements_with_problems=len(req_ids),
        findings_total=len(rows),
    )


def _row(
    *,
    cov,
    ctrl,
    req_title: dict[str, str],
    taxonomy: str,
    gap: str,
    mapped: bool,
    severity: str,
    owner: str | None = None,
    deadline: str | None = None,
) -> GapRow:
    return GapRow(
        framework_id=cov.framework_id,
        framework_name=cov.framework_name,
        framework_version=cov.framework_version,
        requirement_id=cov.requirement_id,
        requirement_code=cov.requirement_code,
        requirement_title=req_title.get(cov.requirement_id, ""),
        canonical_control_ref=ctrl.canonical_control_ref,
        control_name=ctrl.name,
        mapping=cov.relation.value,
        status=ctrl.status.value if hasattr(ctrl.status, "value") else str(ctrl.status),
        owner=owner if owner is not None else ctrl.owner,
        deadline=deadline if deadline is not None else ctrl.due_date,
        priority=ctrl.priority,
        evidence_count=ctrl.evidence_count,
        open_task_count=ctrl.open_task_count,
        gap=gap,
        notes=cov.rationale or "",
        mapped=mapped,
        taxonomy=taxonomy,
        severity=severity,
    )


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
    if flt.taxonomy:
        tax = flt.taxonomy.upper()
        out = [r for r in out if (r.taxonomy or "").upper() == tax]
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
        out = [r for r in out if r.taxonomy == GapTaxonomy.EVIDENCE]
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
            or q in (r.taxonomy or "").lower()
        ]
    return out


def overdue_gap_rows(rows: list[GapRow], *, as_of: date | None = None) -> list[GapRow]:
    return [r for r in rows if is_overdue(r.deadline, as_of=as_of)]

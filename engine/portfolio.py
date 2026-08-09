from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .authz import assert_tenant_access
from .checklist import build_unified_checklist
from .dates import is_overdue, is_upcoming, today
from .domain import ImplementationStatus, ProgramSnapshot
from .impact import rank_control_impact
from .program_loader import load_program_snapshot
from .readiness import framework_readiness


FIXTURES = Path(__file__).resolve().parent / "fixtures"
DEFAULT_REGISTRY = FIXTURES / "portfolio_registry.json"


@dataclass
class PortfolioClientRow:
    tenant_id: str
    tenant_name: str
    program_id: str
    program_name: str
    frameworks: list[str]
    implementation_readiness: float | None
    critical_gaps: int
    high_priority_open: int
    overdue_tasks: int
    next_deadline: str | None
    last_activity: str | None
    raw_requirements: int
    unified_controls: int
    unmapped: int


@dataclass
class ClientDashboard:
    tenant_id: str
    tenant_name: str
    program_id: str
    program_name: str
    frameworks: list[dict]
    raw_requirements: int
    unified_controls: int
    status_counts: dict[str, int]
    unmapped_count: int
    missing_evidence: int
    open_tasks: int
    overdue_tasks: int
    deadlines_next_30_days: list[dict]
    readiness: list[dict]
    workload_by_owner: dict[str, int]
    top_impact: list[dict] = field(default_factory=list)
    scope: str = ""
    program_status: str = "ACTIVE"
    available_framework_versions: list[dict] = field(default_factory=list)


def load_portfolio_programs(
    registry_path: Path | None = None,
) -> list[tuple[ProgramSnapshot, str | None]]:
    path = registry_path or DEFAULT_REGISTRY
    raw = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    out: list[tuple[ProgramSnapshot, str | None]] = []
    for entry in raw.get("programs", []):
        snap_name = entry["snapshot"]
        snap_path = Path(snap_name)
        if not snap_path.is_file():
            snap_path = base / snap_name
        program = load_program_snapshot(snap_path)
        out.append((program, entry.get("last_activity")))
    return out


def build_portfolio(
    *,
    actor_tenant_ids: set[str],
    is_superuser: bool,
    registry_path: Path | None = None,
    as_of=None,
) -> list[PortfolioClientRow]:
    """Global consultant portfolio — tenant-filtered server-side."""
    as_of = as_of or today()
    rows: list[PortfolioClientRow] = []
    for program, last_activity in load_portfolio_programs(registry_path):
        decision = assert_tenant_access(
            actor_tenant_ids=actor_tenant_ids,
            is_superuser=is_superuser,
            target_tenant_id=program.tenant_id,
        )
        if not decision.allowed:
            continue
        rows.append(_portfolio_row(program, last_activity, as_of=as_of))
    rows.sort(key=lambda r: r.tenant_name.lower())
    return rows


def build_client_dashboard(
    program: ProgramSnapshot, *, as_of=None
) -> ClientDashboard:
    as_of = as_of or today()
    checklist = build_unified_checklist(program)
    readiness = framework_readiness(program, checklist)
    impact = rank_control_impact(program, checklist)

    status_counts = {s.value: 0 for s in ImplementationStatus}
    missing_evidence = 0
    open_tasks = 0
    overdue_tasks = 0
    deadlines: list[dict] = []
    workload: dict[str, int] = {}
    frameworks: dict[str, dict] = {}

    for ctrl in checklist.controls:
        status_counts[ctrl.status.value] = status_counts.get(ctrl.status.value, 0) + 1
        if ctrl.evidence_count <= 0 and ctrl.status != ImplementationStatus.NOT_APPLICABLE:
            missing_evidence += 1
        open_tasks += ctrl.open_task_count
        if is_overdue(ctrl.due_date, as_of=as_of) and ctrl.open_task_count > 0:
            overdue_tasks += ctrl.open_task_count
        elif is_overdue(ctrl.due_date, as_of=as_of) and ctrl.status != ImplementationStatus.IMPLEMENTED:
            overdue_tasks += 1
        if is_upcoming(ctrl.due_date, days=30, as_of=as_of):
            deadlines.append(
                {
                    "control_ref": ctrl.canonical_control_ref,
                    "name": ctrl.name,
                    "due_date": ctrl.due_date,
                    "owner": ctrl.owner,
                    "status": ctrl.status.value,
                }
            )
        owner = ctrl.owner or "(unassigned)"
        if ctrl.status != ImplementationStatus.IMPLEMENTED:
            workload[owner] = workload.get(owner, 0) + 1
        for cov in ctrl.framework_coverage:
            frameworks[cov.framework_id] = {
                "framework_id": cov.framework_id,
                "framework_name": cov.framework_name,
                "framework_version": cov.framework_version,
            }

    deadlines.sort(key=lambda d: d["due_date"] or "9999")

    # Prefer explicit remediation tasks when present in the program overlay.
    if program.tasks:
        open_tasks = sum(
            1 for t in program.tasks if (t.status or "").upper() != "DONE"
        )
        overdue_tasks = sum(
            1
            for t in program.tasks
            if (t.status or "").upper() != "DONE"
            and is_overdue(t.due_date, as_of=as_of)
        )

    return ClientDashboard(
        tenant_id=program.tenant_id,
        tenant_name=program.tenant_name,
        program_id=program.program_id,
        program_name=program.program_name,
        frameworks=sorted(frameworks.values(), key=lambda f: f["framework_name"]),
        raw_requirements=checklist.raw_requirement_count,
        unified_controls=checklist.unified_control_count,
        status_counts=status_counts,
        unmapped_count=len(checklist.unmapped),
        missing_evidence=missing_evidence,
        open_tasks=open_tasks,
        overdue_tasks=overdue_tasks,
        deadlines_next_30_days=deadlines,
        readiness=[
            {
                "framework_name": r.framework_name,
                "framework_version": r.framework_version,
                "implementation_readiness": r.implementation_readiness,
                "fully_covered": r.fully_covered,
                "partially_covered": r.partially_covered,
                "not_covered": r.not_covered,
                "unmapped": r.unmapped,
                "not_applicable": r.not_applicable,
            }
            for r in readiness
        ],
        workload_by_owner=dict(sorted(workload.items())),
        top_impact=[
            {
                "canonical_control_ref": i.canonical_control_ref,
                "summary": i.readable_summary,
                "open_gap_requirements": i.open_gap_requirements,
            }
            for i in impact[:5]
        ],
        scope=program.scope or "",
        program_status=program.program_status or "ACTIVE",
        available_framework_versions=list(program.available_framework_versions or []),
    )


def _portfolio_row(
    program: ProgramSnapshot, last_activity: str | None, *, as_of
) -> PortfolioClientRow:
    checklist = build_unified_checklist(program)
    readiness = framework_readiness(program, checklist)
    readiness_vals = [
        r.implementation_readiness
        for r in readiness
        if r.implementation_readiness is not None
    ]
    impl_ready = (
        sum(readiness_vals) / len(readiness_vals) if readiness_vals else None
    )
    frameworks = sorted(
        {
            f"{c.framework_name}@{c.framework_version}"
            for ctrl in checklist.controls
            for c in ctrl.framework_coverage
        }
        | {
            f"{u.framework_name}@{u.framework_version}"
            for u in checklist.unmapped
        }
    )
    critical = sum(
        1
        for c in checklist.controls
        if c.status == ImplementationStatus.NOT_IMPLEMENTED
        and (c.priority or "").upper() == "HIGH"
    )
    high_open = sum(
        1
        for c in checklist.controls
        if c.status != ImplementationStatus.IMPLEMENTED
        and (c.priority or "").upper() == "HIGH"
    )
    overdue = 0
    next_deadline = None
    for c in checklist.controls:
        if c.open_task_count and is_overdue(c.due_date, as_of=as_of):
            overdue += c.open_task_count
        elif is_overdue(c.due_date, as_of=as_of) and c.status != ImplementationStatus.IMPLEMENTED:
            overdue += 1
        if c.due_date and (
            next_deadline is None or c.due_date < next_deadline
        ):
            if c.status != ImplementationStatus.IMPLEMENTED or c.open_task_count:
                next_deadline = c.due_date

    return PortfolioClientRow(
        tenant_id=program.tenant_id,
        tenant_name=program.tenant_name,
        program_id=program.program_id,
        program_name=program.program_name,
        frameworks=frameworks,
        implementation_readiness=impl_ready,
        critical_gaps=critical,
        high_priority_open=high_open,
        overdue_tasks=overdue,
        next_deadline=next_deadline,
        last_activity=last_activity,
        raw_requirements=checklist.raw_requirement_count,
        unified_controls=checklist.unified_control_count,
        unmapped=len(checklist.unmapped),
    )

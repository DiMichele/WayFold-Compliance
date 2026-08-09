from __future__ import annotations

from .checklist import build_unified_checklist
from .domain import ControlImpactRow, ImplementationStatus, ProgramSnapshot, UnifiedChecklist


def rank_control_impact(
    program: ProgramSnapshot,
    checklist: UnifiedChecklist | None = None,
    *,
    only_open_gaps: bool = True,
) -> list[ControlImpactRow]:
    """Readable control impact / ROI — not an opaque score.

    Example summary: "Impacts 5 open-gap requirements across 3 frameworks".
    """
    checklist = checklist or build_unified_checklist(program)
    rows: list[ControlImpactRow] = []

    for ctrl in checklist.controls:
        frameworks = {c.framework_id for c in ctrl.framework_coverage}
        reqs = {c.requirement_id for c in ctrl.framework_coverage}
        open_gap = 0
        if only_open_gaps:
            if ctrl.status != ImplementationStatus.IMPLEMENTED:
                open_gap = len(reqs)
            else:
                # Implemented FULL still may leave PARTIAL deltas open
                open_gap = sum(
                    1
                    for c in ctrl.framework_coverage
                    if c.relation.value in {"PARTIAL", "SUPPORTING"} and c.uncovered_delta
                )
        else:
            open_gap = len(reqs)

        summary = (
            f"Impatta {len(reqs)} requisiti"
            f"{' non completamente coperti' if open_gap else ''}"
            f" su {len(frameworks)} framework"
            f" ({open_gap} segnali di gap aperti); stato={ctrl.status.value}"
        )
        rows.append(
            ControlImpactRow(
                control_key=ctrl.control_key,
                canonical_control_ref=ctrl.canonical_control_ref,
                name=ctrl.name,
                status=ctrl.status,
                frameworks_impacted=len(frameworks),
                requirements_impacted=len(reqs),
                open_gap_requirements=open_gap,
                readable_summary=summary,
            )
        )

    rows.sort(
        key=lambda r: (
            -r.open_gap_requirements,
            -r.frameworks_impacted,
            -r.requirements_impacted,
            r.canonical_control_ref or r.name,
        )
    )
    return rows

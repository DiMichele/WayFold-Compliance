from __future__ import annotations

from collections import defaultdict

from .checklist import build_unified_checklist
from .domain import (
    CoverageRelation,
    FrameworkReadinessRow,
    ImplementationStatus,
    ProgramSnapshot,
    RequirementCoverage,
    UnifiedChecklist,
)


def _requirement_coverage(
    relation: CoverageRelation | None,
    status: ImplementationStatus | None,
    result: str | None,
) -> RequirementCoverage:
    if (result or "").lower() == "not_applicable":
        return RequirementCoverage.NOT_APPLICABLE
    if relation is None or relation == CoverageRelation.NEEDS_REVIEW:
        # No approved WayFold mapping — never overstate readiness
        return RequirementCoverage.UNMAPPED
    if status in (None, ImplementationStatus.NOT_IMPLEMENTED):
        return RequirementCoverage.NOT_COVERED
    if relation == CoverageRelation.FULL and status == ImplementationStatus.IMPLEMENTED:
        return RequirementCoverage.FULLY_COVERED
    if relation == CoverageRelation.PARTIAL:
        # PARTIAL never auto-promotes to FULL even if implemented
        if status in (
            ImplementationStatus.IMPLEMENTED,
            ImplementationStatus.IN_PROGRESS,
        ):
            return RequirementCoverage.PARTIALLY_COVERED
        return RequirementCoverage.NOT_COVERED
    if relation == CoverageRelation.SUPPORTING:
        if status == ImplementationStatus.IMPLEMENTED:
            return RequirementCoverage.PARTIALLY_COVERED
        return RequirementCoverage.NOT_COVERED
    if relation == CoverageRelation.FULL and status == ImplementationStatus.IN_PROGRESS:
        return RequirementCoverage.PARTIALLY_COVERED
    return RequirementCoverage.NOT_COVERED


def framework_readiness(
    program: ProgramSnapshot, checklist: UnifiedChecklist | None = None
) -> list[FrameworkReadinessRow]:
    checklist = checklist or build_unified_checklist(program)

    # Index best mapping+impl coverage per requirement
    req_best: dict[str, tuple[CoverageRelation | None, ImplementationStatus | None]] = {}
    for ctrl in checklist.controls:
        for cov in ctrl.framework_coverage:
            prev = req_best.get(cov.requirement_id)
            cand = (cov.relation, ctrl.status)
            if prev is None:
                req_best[cov.requirement_id] = cand
                continue
            # Prefer FULL over PARTIAL/SUPPORTING for "best mapping", but never
            # hide PARTIAL semantics in breakdown — store the strictest product view:
            # if any PARTIAL exists alongside FULL to same req, keep PARTIAL if that
            # mapping is the one recorded (multiple mappings unusual per req+control).
            prev_rel, prev_status = prev
            rank = {
                CoverageRelation.FULL: 3,
                CoverageRelation.PARTIAL: 2,
                CoverageRelation.SUPPORTING: 1,
                CoverageRelation.NEEDS_REVIEW: 0,
            }
            if rank.get(cand[0], 0) > rank.get(prev_rel, 0):
                req_best[cov.requirement_id] = cand
            elif cand[0] == prev_rel and _status_rank(cand[1]) > _status_rank(prev_status):
                req_best[cov.requirement_id] = cand

    unmapped_ids = {u.requirement_id for u in checklist.unmapped}
    by_fw: dict[str, dict] = {}
    seen_req: set[str] = set()

    for req in program.requirements:
        if not (req.assessable and req.is_leaf):
            continue
        if req.id in seen_req:
            continue
        seen_req.add(req.id)
        fw_key = req.framework_id
        bucket = by_fw.setdefault(
            fw_key,
            {
                "framework_id": req.framework_id,
                "framework_name": req.framework_name,
                "framework_version": req.framework_version,
                "breakdown": {},
                "counts": defaultdict(int),
                "implemented_applicable": 0,
                "applicable_total": 0,
            },
        )
        if req.id in unmapped_ids:
            cov = RequirementCoverage.UNMAPPED
        else:
            rel, status = req_best.get(req.id, (None, None))
            cov = _requirement_coverage(rel, status, req.result)
        bucket["breakdown"][req.id] = cov
        bucket["counts"][cov.value] += 1
        if cov != RequirementCoverage.NOT_APPLICABLE:
            bucket["applicable_total"] += 1
            if cov == RequirementCoverage.FULLY_COVERED:
                bucket["implemented_applicable"] += 1

    rows: list[FrameworkReadinessRow] = []
    for bucket in by_fw.values():
        applicable = bucket["applicable_total"]
        implemented = bucket["implemented_applicable"]
        readiness = (implemented / applicable) if applicable else None
        counts = bucket["counts"]
        rows.append(
            FrameworkReadinessRow(
                framework_id=bucket["framework_id"],
                framework_name=bucket["framework_name"],
                framework_version=bucket["framework_version"],
                fully_covered=counts.get(RequirementCoverage.FULLY_COVERED.value, 0),
                partially_covered=counts.get(RequirementCoverage.PARTIALLY_COVERED.value, 0),
                not_covered=counts.get(RequirementCoverage.NOT_COVERED.value, 0),
                unmapped=counts.get(RequirementCoverage.UNMAPPED.value, 0),
                not_applicable=counts.get(RequirementCoverage.NOT_APPLICABLE.value, 0),
                applicable_total=applicable,
                implemented_applicable=implemented,
                implementation_readiness=readiness,
                requirement_breakdown=bucket["breakdown"],
            )
        )
    rows.sort(key=lambda r: r.framework_name)
    return rows


def _status_rank(status: ImplementationStatus | None) -> int:
    if status is None:
        return -1
    order = {
        ImplementationStatus.NOT_IMPLEMENTED: 0,
        ImplementationStatus.IN_PROGRESS: 1,
        ImplementationStatus.IMPLEMENTED: 2,
        ImplementationStatus.NOT_APPLICABLE: 3,
    }
    return order.get(status, 0)

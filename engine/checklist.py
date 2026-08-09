from __future__ import annotations

from collections import defaultdict

from .domain import (
    ChecklistControlRow,
    ControlImplementationSnapshot,
    CoverageRelation,
    FrameworkCoverageRow,
    ImplementationStatus,
    MappingRecord,
    ProgramSnapshot,
    RequirementSnapshot,
    UnifiedChecklist,
    UnmappedRequirementRow,
)


def _impl_by_id(program: ProgramSnapshot) -> dict[str, ControlImplementationSnapshot]:
    return {i.id: i for i in program.implementations}


def _mappings_by_requirement(program: ProgramSnapshot) -> dict[str, list[MappingRecord]]:
    out: dict[str, list[MappingRecord]] = defaultdict(list)
    for m in program.mappings:
        if m.review_status.value == "REJECTED":
            continue
        # Prefer APPROVED / HUMAN_REVIEWED; still include DRAFT for visibility
        out[m.requirement_id].append(m)
    return out


def _control_key(mapping: MappingRecord | None, impl: ControlImplementationSnapshot | None) -> str:
    if mapping and mapping.canonical_control_ref:
        return f"canon:{mapping.canonical_control_ref}"
    if impl and impl.canonical_control_ref:
        return f"canon:{impl.canonical_control_ref}"
    if impl and impl.ref_id:
        return f"impl-ref:{impl.ref_id}"
    if impl:
        return f"impl:{impl.id}"
    if mapping:
        return f"canon:{mapping.canonical_control_id}"
    raise ValueError("cannot derive control key")


def build_unified_checklist(program: ProgramSnapshot) -> UnifiedChecklist:
    """Build unified checklist from pinned frameworks + approved mappings.

    Algorithm (master plan §34):
    1. pinned framework versions (already in requirement snapshots)
    2. applicable leaf requirements
    3. valid mappings
    4. resolve canonical controls
    5. deduplicate
    6. preserve deltas
    7. identify UNMAPPED
    8. attach client implementations when present
    """
    # Deduplicate requirements by id (live CISO exports may repeat rows)
    seen_req: set[str] = set()
    leaves: list[RequirementSnapshot] = []
    for r in program.requirements:
        if not (r.assessable and r.is_leaf):
            continue
        if r.id in seen_req:
            continue
        seen_req.add(r.id)
        leaves.append(r)

    maps = _mappings_by_requirement(program)
    impls = _impl_by_id(program)
    links = program.requirement_implementation_links

    grouped: dict[str, dict] = {}
    unmapped: list[UnmappedRequirementRow] = []

    for req in leaves:
        # Deduplicate mappings per requirement+control
        raw_maps = maps.get(req.id, [])
        seen_m: set[tuple[str, str]] = set()
        req_maps: list[MappingRecord] = []
        for m in raw_maps:
            mk = (m.canonical_control_ref, m.relation.value)
            if mk in seen_m:
                continue
            seen_m.add(mk)
            req_maps.append(m)
        linked_impl_ids = list(dict.fromkeys(links.get(req.id, [])))

        if not req_maps and not linked_impl_ids:
            unmapped.append(
                UnmappedRequirementRow(
                    requirement_id=req.id,
                    framework_id=req.framework_id,
                    framework_name=req.framework_name,
                    framework_version=req.framework_version,
                    code=req.code,
                    title=req.title,
                    result=req.result,
                )
            )
            continue

        # Prefer explicit WayFold mappings; fall back to core AppliedControl links
        if req_maps:
            for m in req_maps:
                # Prefer implementation matching canonical ref
                impl = _pick_implementation(m, linked_impl_ids, impls)
                key = _control_key(m, impl)
                bucket = grouped.setdefault(
                    key,
                    {
                        "mapping_samples": [],
                        "impl": impl,
                        "coverages": [],
                        "coverage_keys": set(),
                    },
                )
                if impl and (bucket["impl"] is None or _status_rank(impl.status) > _status_rank(bucket["impl"].status)):
                    bucket["impl"] = impl
                bucket["mapping_samples"].append(m)
                cov_key = (m.requirement_id, m.canonical_control_ref, m.relation.value)
                if cov_key not in bucket["coverage_keys"]:
                    bucket["coverage_keys"].add(cov_key)
                    bucket["coverages"].append(
                        FrameworkCoverageRow(
                            framework_id=m.framework_id,
                            framework_name=m.framework_name,
                            framework_version=m.framework_version,
                            requirement_id=m.requirement_id,
                            requirement_code=m.requirement_code,
                            relation=m.relation,
                            uncovered_delta=m.uncovered_delta,
                            rationale=m.rationale,
                        )
                    )
        else:
            for iid in linked_impl_ids:
                impl = impls.get(iid)
                if not impl:
                    continue
                key = _control_key(None, impl)
                bucket = grouped.setdefault(
                    key,
                    {
                        "mapping_samples": [],
                        "impl": impl,
                        "coverages": [],
                        "coverage_keys": set(),
                    },
                )
                bucket["impl"] = impl
                cov_key = (req.id, impl.ref_id or impl.id, CoverageRelation.FULL.value)
                if cov_key not in bucket["coverage_keys"]:
                    bucket["coverage_keys"].add(cov_key)
                    bucket["coverages"].append(
                        FrameworkCoverageRow(
                            framework_id=req.framework_id,
                            framework_name=req.framework_name,
                            framework_version=req.framework_version,
                            requirement_id=req.id,
                            requirement_code=req.code,
                            relation=CoverageRelation.FULL,
                            uncovered_delta="",
                            rationale="Linked via core AppliedControl (implicit FULL)",
                        )
                    )

    controls: list[ChecklistControlRow] = []
    for key, bucket in grouped.items():
        impl: ControlImplementationSnapshot | None = bucket["impl"]
        samples: list[MappingRecord] = bucket["mapping_samples"]
        coverages: list[FrameworkCoverageRow] = bucket["coverages"]
        gap_parts = [c.uncovered_delta for c in coverages if c.uncovered_delta]
        primary = samples[0] if samples else None
        controls.append(
            ChecklistControlRow(
                control_key=key,
                canonical_control_id=(
                    primary.canonical_control_id
                    if primary
                    else (impl.canonical_control_id if impl else None)
                ),
                canonical_control_ref=(
                    primary.canonical_control_ref
                    if primary
                    else (impl.canonical_control_ref if impl else None)
                ),
                implementation_id=impl.id if impl else None,
                name=(
                    impl.name
                    if impl
                    else (primary.canonical_control_ref if primary else key)
                ),
                status=impl.status if impl else ImplementationStatus.NOT_IMPLEMENTED,
                owner=impl.owner if impl else None,
                due_date=impl.due_date if impl else None,
                priority=impl.priority if impl else None,
                evidence_count=impl.evidence_count if impl else 0,
                open_task_count=impl.open_task_count if impl else 0,
                framework_coverage=coverages,
                gap_notes="; ".join(gap_parts),
            )
        )

    controls.sort(key=lambda c: (c.canonical_control_ref or c.name or c.control_key))
    unmapped.sort(key=lambda u: (u.framework_name, u.code))

    return UnifiedChecklist(
        tenant_id=program.tenant_id,
        program_id=program.program_id,
        program_name=program.program_name,
        raw_requirement_count=len(leaves),
        unified_control_count=len(controls),
        unmapped=unmapped,
        controls=controls,
        meta={
            "mapping_count": len(program.mappings),
            "implementation_count": len(program.implementations),
        },
    )


def _pick_implementation(
    mapping: MappingRecord,
    linked_impl_ids: list[str],
    impls: dict[str, ControlImplementationSnapshot],
) -> ControlImplementationSnapshot | None:
    for iid in linked_impl_ids:
        impl = impls.get(iid)
        if not impl:
            continue
        if impl.canonical_control_ref and impl.canonical_control_ref == mapping.canonical_control_ref:
            return impl
        if impl.ref_id and impl.ref_id == mapping.canonical_control_ref:
            return impl
    # any linked impl, or global impl matching ref
    for iid in linked_impl_ids:
        if iid in impls:
            return impls[iid]
    for impl in impls.values():
        if impl.canonical_control_ref == mapping.canonical_control_ref:
            return impl
        if impl.ref_id == mapping.canonical_control_ref:
            return impl
    return None


def _status_rank(status: ImplementationStatus) -> int:
    order = {
        ImplementationStatus.NOT_IMPLEMENTED: 0,
        ImplementationStatus.IN_PROGRESS: 1,
        ImplementationStatus.IMPLEMENTED: 2,
        ImplementationStatus.NOT_APPLICABLE: 3,
    }
    return order.get(status, 0)


def map_ciso_applied_status(status: str | None) -> ImplementationStatus:
    s = (status or "").lower()
    if s in {"active"}:
        return ImplementationStatus.IMPLEMENTED
    if s in {"in_progress", "on_hold", "degraded"}:
        return ImplementationStatus.IN_PROGRESS
    if s in {"deprecated"}:
        return ImplementationStatus.NOT_APPLICABLE
    return ImplementationStatus.NOT_IMPLEMENTED

from __future__ import annotations

from pathlib import Path

from engine.portfolio import DEFAULT_REGISTRY, load_portfolio_programs
from engine.program_loader import load_program_snapshot

from .domain import ClientImpactReport, ClientImpactRow, RegulatoryChange, Source
from .store import RegulatoryStore


def project_client_impact(
    change: RegulatoryChange,
    source: Source,
    *,
    store: RegulatoryStore | None = None,  # noqa: ARG001 — reserved for future
    registry_path: Path | None = None,
    extra_programs: list | None = None,
    actor_tenant_ids: set[str] | None = None,
    is_superuser: bool = False,
) -> ClientImpactReport:
    """Deterministic impact: source links → requirements/controls → pinned programs.

    Does NOT migrate client baselines. Indication only.
    Tenant isolation: non-superuser actors only see programs in actor_tenant_ids.
    """
    req_ids = set(change.potentially_impacted_requirement_ids or source.linked_requirement_ids)
    fw_ids = set(source.linked_framework_ids)
    fw_versions = set(source.linked_framework_versions)
    control_refs = set(change.potentially_impacted_control_refs)

    programs = []
    if extra_programs:
        programs.extend(extra_programs)
    else:
        programs.extend(p for p, _ in load_portfolio_programs(registry_path or DEFAULT_REGISTRY))

    if not is_superuser:
        allowed = set(actor_tenant_ids or ())
        programs = [p for p in programs if p.tenant_id in allowed]

    rows: list[ClientImpactRow] = []
    for program in programs:
        # Index mappings for this program
        matched_reqs: list[str] = []
        matched_controls: list[str] = []
        matched_fw: dict[str, tuple[str, str, str]] = {}

        for req in program.requirements:
            hit = False
            if req.id in req_ids or req.code in req_ids:
                hit = True
            if fw_ids and req.framework_id in fw_ids:
                if not fw_versions or req.framework_version in fw_versions:
                    # framework-level link without specific req still counts if req linked empty
                    if not req_ids:
                        hit = True
            if hit:
                matched_reqs.append(req.id)
                matched_fw[req.framework_id] = (
                    req.framework_id,
                    req.framework_name,
                    req.framework_version,
                )

        for m in program.mappings:
            if m.requirement_id in matched_reqs or m.requirement_code in req_ids:
                matched_controls.append(m.canonical_control_ref)
                control_refs.add(m.canonical_control_ref)
                matched_fw[m.framework_id] = (
                    m.framework_id,
                    m.framework_name,
                    m.framework_version,
                )

        # Also match by control refs already on the change
        for impl in program.implementations:
            ref = impl.canonical_control_ref
            if ref and ref in change.potentially_impacted_control_refs:
                matched_controls.append(ref)

        if not matched_reqs and not matched_controls and not (
            fw_ids & {r.framework_id for r in program.requirements}
        ):
            continue
        if fw_ids and not (fw_ids & set(matched_fw.keys())):
            # program has no overlapping framework
            prog_fws = {r.framework_id for r in program.requirements}
            if not (fw_ids & prog_fws):
                continue
            for r in program.requirements:
                if r.framework_id in fw_ids:
                    matched_fw[r.framework_id] = (
                        r.framework_id,
                        r.framework_name,
                        r.framework_version,
                    )

        if not matched_fw and matched_reqs:
            for r in program.requirements:
                if r.id in matched_reqs:
                    matched_fw[r.framework_id] = (
                        r.framework_id,
                        r.framework_name,
                        r.framework_version,
                    )

        for fw_id, (fid, fname, fver) in matched_fw.items():
            rows.append(
                ClientImpactRow(
                    tenant_id=program.tenant_id,
                    tenant_name=program.tenant_name,
                    program_id=program.program_id,
                    program_name=program.program_name,
                    framework_id=fid,
                    framework_name=fname,
                    framework_version=fver,
                    requirement_ids=sorted(set(matched_reqs)),
                    control_refs=sorted(set(matched_controls) | control_refs),
                )
            )

    clients = {r.tenant_id for r in rows}
    programs_ids = {r.program_id for r in rows}
    all_reqs = {rid for r in rows for rid in r.requirement_ids}
    all_ctrls = {c for r in rows for c in r.control_refs}

    return ClientImpactReport(
        change_id=change.id,
        source_id=source.id,
        requirements=len(all_reqs),
        controls=len(all_ctrls),
        clients=len(clients),
        programs=len(programs_ids),
        rows=rows,
    )


def resolve_controls_for_requirements(
    requirement_ids: list[str], *, registry_path: Path | None = None
) -> list[str]:
    refs: set[str] = set()
    for program, _ in load_portfolio_programs(registry_path or DEFAULT_REGISTRY):
        for m in program.mappings:
            if m.requirement_id in requirement_ids or m.requirement_code in requirement_ids:
                refs.add(m.canonical_control_ref)
    return sorted(refs)


def load_demo_programs() -> list:
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    return [
        load_program_snapshot(fixtures / "michele_phase2_program.json"),
        load_program_snapshot(fixtures / "alfa_phase3_program.json"),
    ]

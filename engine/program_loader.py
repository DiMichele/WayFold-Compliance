from __future__ import annotations

import json
from pathlib import Path

from .domain import (
    ControlImplementationSnapshot,
    CoverageRelation,
    EvidenceSnapshot,
    ImplementationStatus,
    MappingRecord,
    ProgramSnapshot,
    RemediationTaskSnapshot,
    RequirementSnapshot,
    ReviewStatus,
)


def load_program_snapshot(path: Path) -> ProgramSnapshot:
    raw = json.loads(path.read_text(encoding="utf-8"))
    requirements = [
        RequirementSnapshot(
            id=r["id"],
            framework_id=r["framework_id"],
            framework_name=r["framework_name"],
            framework_version=str(r.get("framework_version", "")),
            code=r["code"],
            title=r["title"],
            assessable=bool(r.get("assessable", True)),
            is_leaf=bool(r.get("is_leaf", True)),
            result=r.get("result"),
        )
        for r in raw["requirements"]
    ]
    implementations = [
        ControlImplementationSnapshot(
            id=i["id"],
            ref_id=i["ref_id"],
            name=i["name"],
            canonical_control_id=i.get("canonical_control_id"),
            canonical_control_ref=i.get("canonical_control_ref"),
            status=ImplementationStatus(i["status"]),
            owner=i.get("owner"),
            due_date=i.get("due_date"),
            priority=i.get("priority"),
            evidence_count=int(i.get("evidence_count", 0)),
            open_task_count=int(i.get("open_task_count", 0)),
            folder_id=i.get("folder_id"),
            description=str(i.get("description") or ""),
            not_applicable_rationale=str(i.get("not_applicable_rationale") or ""),
            not_applicable_approved_by=i.get("not_applicable_approved_by"),
            not_applicable_approved_at=i.get("not_applicable_approved_at"),
        )
        for i in raw["implementations"]
    ]
    mappings = [
        MappingRecord(
            requirement_id=m["requirement_id"],
            framework_id=m["framework_id"],
            framework_name=m["framework_name"],
            framework_version=str(m.get("framework_version", "")),
            requirement_code=m["requirement_code"],
            canonical_control_id=m["canonical_control_id"],
            canonical_control_ref=m["canonical_control_ref"],
            relation=CoverageRelation(m["relation"]),
            rationale=m.get("rationale", ""),
            uncovered_delta=m.get("uncovered_delta", ""),
            notes=m.get("notes", ""),
            confidence=m.get("confidence"),
            review_status=ReviewStatus(m.get("review_status", "APPROVED")),
        )
        for m in raw["mappings"]
    ]
    evidences = [
        EvidenceSnapshot(
            id=e["id"],
            title=e["title"],
            filename=e.get("filename") or e["title"],
            control_refs=list(e.get("control_refs") or []),
            status=str(e.get("status") or "VALID"),
            valid_until=e.get("valid_until"),
            review_by=e.get("review_by"),
            notes=str(e.get("notes") or ""),
        )
        for e in raw.get("evidences") or []
    ]
    tasks = [
        RemediationTaskSnapshot(
            id=t["id"],
            title=t["title"],
            control_ref=t.get("control_ref"),
            owner=t.get("owner"),
            status=str(t.get("status") or "TODO"),
            due_date=t.get("due_date"),
            priority=t.get("priority"),
            notes=str(t.get("notes") or ""),
        )
        for t in raw.get("tasks") or []
    ]
    return ProgramSnapshot(
        tenant_id=raw["tenant_id"],
        tenant_name=raw["tenant_name"],
        program_id=raw["program_id"],
        program_name=raw["program_name"],
        requirements=requirements,
        implementations=implementations,
        mappings=mappings,
        requirement_implementation_links=raw.get("requirement_implementation_links", {}),
        scope=str(raw.get("scope") or ""),
        program_status=str(raw.get("program_status") or "ACTIVE"),
        dataset_marker=str(raw.get("dataset_marker") or ""),
        evidences=evidences,
        tasks=tasks,
        available_framework_versions=list(raw.get("available_framework_versions") or []),
    )

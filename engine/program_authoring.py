"""Client / program creation and unified checklist generation from published versions."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.checklist import build_unified_checklist
from engine.control_catalog import get_by_code, list_controls
from engine.domain import (
    ControlImplementationSnapshot,
    CoverageRelation,
    ImplementationStatus,
    MappingRecord,
    ProgramSnapshot,
    RequirementSnapshot,
    ReviewStatus,
)
from engine.framework_versions import VersionStatus, get_version, list_versions
from engine import kb_mappings
from engine.program_loader import load_program_snapshot
from engine.runtime_paths import data_root


def programs_dir() -> Path:
    d = data_root() / "programs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return s[:40] or secrets.token_hex(3)


def _snapshot_to_dict(program: ProgramSnapshot) -> dict[str, Any]:
    return {
        "tenant_id": program.tenant_id,
        "tenant_name": program.tenant_name,
        "program_id": program.program_id,
        "program_name": program.program_name,
        "scope": program.scope,
        "program_status": program.program_status,
        "dataset_marker": program.dataset_marker,
        "requirements": [asdict(r) for r in program.requirements],
        "implementations": [
            {
                **asdict(i),
                "status": i.status.value if hasattr(i.status, "value") else i.status,
            }
            for i in program.implementations
        ],
        "mappings": [
            {
                **{k: v for k, v in asdict(m).items() if k not in {"relation", "review_status"}},
                "relation": m.relation.value,
                "review_status": m.review_status.value,
            }
            for m in program.mappings
        ],
        "requirement_implementation_links": program.requirement_implementation_links,
        "evidences": [asdict(e) for e in program.evidences],
        "tasks": [asdict(t) for t in program.tasks],
        "available_framework_versions": list(program.available_framework_versions or []),
        "owner": getattr(program, "owner", "") or "",
        "description": getattr(program, "description", "") or "",
    }


def save_program_snapshot(program: ProgramSnapshot, path: Path | None = None) -> Path:
    if path is None:
        path = programs_dir() / f"{_slug(program.program_id)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _snapshot_to_dict(program)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def update_registry(registry_path: Path, *, snapshot_rel: str, program_id: str) -> None:
    if registry_path.is_file():
        try:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {"programs": []}
    else:
        data = {"programs": []}
    programs = list(data.get("programs") or [])
    # Avoid duplicate entries for same snapshot or program_id
    cleaned = []
    for p in programs:
        if p.get("program_id") == program_id:
            continue
        if str(p.get("snapshot") or "").endswith(f"{program_id}.json"):
            continue
        cleaned.append(p)
    cleaned.append(
        {
            "snapshot": snapshot_rel,
            "program_id": program_id,
            "last_activity": __import__("datetime").date.today().isoformat(),
        }
    )
    data["programs"] = cleaned
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def create_client_shell(
    *,
    name: str,
    code: str = "",
    description: str = "",
    contact: str = "",
    status: str = "ACTIVE",
) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise ValueError("name_required")
    code = (code or _slug(name)).strip()
    tenant_id = f"tenant-{_slug(code)}"
    return {
        "tenant_id": tenant_id,
        "tenant_name": name,
        "code": code,
        "description": description.strip(),
        "contact": contact.strip(),
        "status": (status or "ACTIVE").upper(),
    }


def create_program(
    *,
    name: str,
    tenant_id: str,
    tenant_name: str,
    scope: str = "",
    owner: str = "",
    description: str = "",
    status: str = "ACTIVE",
    version_ids: list[str] | None = None,
    registry_path: Path | None = None,
) -> ProgramSnapshot:
    name = name.strip()
    if not name:
        raise ValueError("name_required")
    if not tenant_id:
        raise ValueError("tenant_required")
    version_ids = version_ids or []
    versions = []
    for vid in version_ids:
        ver = get_version(vid)
        if ver is None:
            raise KeyError(f"version_not_found:{vid}")
        if ver.status != VersionStatus.PUBLISHED.value:
            raise ValueError(f"version_not_published:{ver.version}")
        versions.append(ver)

    requirements: list[RequirementSnapshot] = []
    mappings: list[MappingRecord] = []
    impl_by_ref: dict[str, ControlImplementationSnapshot] = {}
    links: dict[str, list[str]] = {}

    for ver in versions:
        for req in ver.requirements:
            is_leaf = getattr(req, "is_leaf", True)
            requirements.append(
                RequirementSnapshot(
                    id=req.id,
                    framework_id=ver.framework_id,
                    framework_name=ver.framework_name,
                    framework_version=ver.version,
                    code=req.code,
                    title=req.title,
                    assessable=bool(is_leaf),
                    is_leaf=bool(is_leaf),
                )
            )
        kb_maps = kb_mappings.list_mappings(
            framework_id=ver.framework_id,
            framework_version=ver.version,
        )
        for m in kb_maps:
            if m.review_status != ReviewStatus.APPROVED:
                continue
            mappings.append(m)
            ref = m.canonical_control_ref
            if ref and ref not in impl_by_ref:
                catalog = get_by_code(ref)
                impl_id = f"impl-{_slug(ref)}"
                impl_by_ref[ref] = ControlImplementationSnapshot(
                    id=impl_id,
                    ref_id=ref,
                    name=(catalog.title if catalog else ref),
                    canonical_control_id=(catalog.id if catalog else ref),
                    canonical_control_ref=ref,
                    status=ImplementationStatus.NOT_IMPLEMENTED,
                    owner=owner or None,
                    priority=(catalog.default_priority if catalog else "MEDIUM"),
                    folder_id=tenant_id,
                    description=(catalog.description if catalog else ""),
                )
            if ref and ref in impl_by_ref:
                links.setdefault(m.requirement_id, []).append(impl_by_ref[ref].id)

    # available versions for banners (newer drafts of same framework)
    available: list[dict[str, Any]] = []
    pinned = {(v.framework_id, v.version) for v in versions}
    for ver in versions:
        for other in list_versions(framework_id=ver.framework_id):
            key = (other.framework_id, other.version)
            available.append(
                {
                    "framework_id": other.framework_id,
                    "framework_name": other.framework_name,
                    "framework_version": other.version,
                    "version": other.version,
                    "status": other.status,
                    "assigned_to_program": key in pinned,
                }
            )

    program = ProgramSnapshot(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        program_id=f"program-{_slug(name)}-{secrets.token_hex(3)}",
        program_name=name,
        requirements=requirements,
        implementations=list(impl_by_ref.values()),
        mappings=mappings,
        requirement_implementation_links=links,
        scope=scope.strip(),
        program_status=(status or "ACTIVE").upper(),
        dataset_marker="",
        evidences=[],
        tasks=[],
        available_framework_versions=available,
        owner=owner.strip(),
        description=description.strip(),
    )

    # Persist under data/programs and register
    snap_path = programs_dir() / f"{program.program_id}.json"
    payload = _snapshot_to_dict(program)
    snap_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if registry_path is not None:
        # Prefer relative path from registry parent when under same data tree
        try:
            rel = str(snap_path.relative_to(registry_path.parent))
        except ValueError:
            rel = str(snap_path)
        update_registry(registry_path, snapshot_rel=rel, program_id=program.program_id)

    return load_program_snapshot(snap_path)


def checklist_preview(version_ids: list[str]) -> dict[str, Any]:
    """Pure in-memory checklist preview — no disk write/delete."""
    version_ids = version_ids or []
    versions = []
    for vid in version_ids:
        ver = get_version(vid)
        if ver is None:
            raise KeyError(f"version_not_found:{vid}")
        if ver.status != VersionStatus.PUBLISHED.value:
            raise ValueError(f"version_not_published:{ver.version}")
        versions.append(ver)

    requirements: list[RequirementSnapshot] = []
    mappings: list[MappingRecord] = []
    impl_by_ref: dict[str, ControlImplementationSnapshot] = {}
    links: dict[str, list[str]] = {}

    for ver in versions:
        for req in ver.requirements:
            is_leaf = getattr(req, "is_leaf", True)
            requirements.append(
                RequirementSnapshot(
                    id=req.id,
                    framework_id=ver.framework_id,
                    framework_name=ver.framework_name,
                    framework_version=ver.version,
                    code=req.code,
                    title=req.title,
                    assessable=bool(is_leaf),
                    is_leaf=bool(is_leaf),
                )
            )
        for m in kb_mappings.list_mappings(
            framework_id=ver.framework_id,
            framework_version=ver.version,
        ):
            if m.review_status != ReviewStatus.APPROVED:
                continue
            mappings.append(m)
            ref = m.canonical_control_ref
            if ref and ref not in impl_by_ref:
                catalog = get_by_code(ref)
                impl_id = f"impl-{_slug(ref)}"
                impl_by_ref[ref] = ControlImplementationSnapshot(
                    id=impl_id,
                    ref_id=ref,
                    name=(catalog.title if catalog else ref),
                    canonical_control_id=(catalog.id if catalog else ref),
                    canonical_control_ref=ref,
                    status=ImplementationStatus.NOT_IMPLEMENTED,
                    priority=(catalog.default_priority if catalog else "MEDIUM"),
                    description=(catalog.description if catalog else ""),
                )
            if ref and ref in impl_by_ref:
                links.setdefault(m.requirement_id, []).append(impl_by_ref[ref].id)

    program = ProgramSnapshot(
        tenant_id="tenant-preview",
        tenant_name="Preview",
        program_id="program-preview-memory",
        program_name="__preview__",
        requirements=requirements,
        implementations=list(impl_by_ref.values()),
        mappings=mappings,
        requirement_implementation_links=links,
    )
    checklist = build_unified_checklist(program)
    return {
        "requirements": len(program.requirements),
        "unified_controls": len(checklist.controls),
        "unmapped": len(checklist.unmapped),
        "controls": [
            {
                "ref": c.canonical_control_ref,
                "name": c.name,
                "frameworks": sorted({x.framework_name for x in c.framework_coverage}),
            }
            for c in checklist.controls
        ],
        "unmapped_codes": [u.code for u in checklist.unmapped],
    }


def persist_control_changes(
    program_path: Path,
    control_id: str,
    changes: dict[str, Any],
) -> ProgramSnapshot:
    """Apply implementation field updates onto a program JSON snapshot."""
    program = load_program_snapshot(program_path)
    impls = []
    found = False
    for impl in program.implementations:
        if impl.id == control_id or impl.ref_id == control_id or impl.canonical_control_ref == control_id:
            found = True
            status = changes.get("status", impl.status)
            if isinstance(status, str):
                status = ImplementationStatus(status)
            impls.append(
                ControlImplementationSnapshot(
                    id=impl.id,
                    ref_id=impl.ref_id,
                    name=str(changes.get("name") or impl.name),
                    canonical_control_id=impl.canonical_control_id,
                    canonical_control_ref=impl.canonical_control_ref,
                    status=status,
                    owner=changes.get("owner", impl.owner),
                    due_date=changes.get("due_date", impl.due_date),
                    priority=changes.get("priority", impl.priority),
                    evidence_count=impl.evidence_count,
                    open_task_count=impl.open_task_count,
                    folder_id=impl.folder_id,
                    description=str(changes.get("description", impl.description) or ""),
                    not_applicable_rationale=str(
                        changes.get("not_applicable_rationale", impl.not_applicable_rationale) or ""
                    ),
                    not_applicable_approved_by=changes.get(
                        "not_applicable_approved_by", impl.not_applicable_approved_by
                    ),
                    not_applicable_approved_at=changes.get(
                        "not_applicable_approved_at", impl.not_applicable_approved_at
                    ),
                )
            )
        else:
            impls.append(impl)
    if not found:
        raise KeyError(control_id)
    # Preserve program-level metadata (owner/description must survive control edits)
    existing_owner = ""
    existing_description = ""
    try:
        raw_existing = json.loads(program_path.read_text(encoding="utf-8"))
        existing_owner = str(raw_existing.get("owner") or program.owner or "")
        existing_description = str(
            raw_existing.get("description") or program.description or ""
        )
    except (OSError, json.JSONDecodeError):
        existing_owner = program.owner or ""
        existing_description = program.description or ""

    updated = ProgramSnapshot(
        tenant_id=program.tenant_id,
        tenant_name=program.tenant_name,
        program_id=program.program_id,
        program_name=program.program_name,
        requirements=program.requirements,
        implementations=impls,
        mappings=program.mappings,
        requirement_implementation_links=program.requirement_implementation_links,
        scope=program.scope,
        program_status=program.program_status,
        dataset_marker=program.dataset_marker,
        evidences=program.evidences,
        tasks=program.tasks,
        available_framework_versions=program.available_framework_versions,
        owner=existing_owner,
        description=existing_description,
    )
    save_program_snapshot(updated, program_path)
    return updated


def find_program_path(program_id: str, registry_path: Path) -> Path | None:
    if not registry_path.is_file():
        return None
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    base = registry_path.parent
    for entry in data.get("programs") or []:
        snap = Path(entry.get("snapshot") or "")
        if not snap.is_file():
            snap = base / snap
        if not snap.is_file():
            continue
        try:
            raw = json.loads(snap.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(raw.get("program_id")) == program_id:
            return snap
    return None


__all__ = [
    "create_client_shell",
    "create_program",
    "checklist_preview",
    "save_program_snapshot",
    "persist_control_changes",
    "find_program_path",
    "programs_dir",
]

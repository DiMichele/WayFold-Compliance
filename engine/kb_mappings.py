"""Global Knowledge Base mappings (requirement ↔ canonical control).

Program snapshots may copy these mappings when a FrameworkVersion is assigned.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict
from pathlib import Path
from typing import Any

from engine.domain import CoverageRelation, MappingRecord, ReviewStatus
from engine.runtime_paths import data_root


def store_path() -> Path:
    return data_root() / "kb_mappings.json"


def _load() -> dict[str, Any]:
    path = store_path()
    if not path.is_file():
        return {"mappings": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"mappings": []}


def _save(data: dict[str, Any]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _to_record(raw: dict[str, Any]) -> MappingRecord:
    return MappingRecord(
        requirement_id=str(raw["requirement_id"]),
        framework_id=str(raw["framework_id"]),
        framework_name=str(raw.get("framework_name") or ""),
        framework_version=str(raw.get("framework_version") or ""),
        requirement_code=str(raw.get("requirement_code") or ""),
        canonical_control_id=str(raw.get("canonical_control_id") or ""),
        canonical_control_ref=str(raw.get("canonical_control_ref") or ""),
        relation=CoverageRelation(str(raw.get("relation") or "FULL")),
        rationale=str(raw.get("rationale") or ""),
        uncovered_delta=str(raw.get("uncovered_delta") or ""),
        notes=str(raw.get("notes") or ""),
        confidence=raw.get("confidence"),
        review_status=ReviewStatus(str(raw.get("review_status") or "DRAFT")),
    )


def _row_id(raw: dict[str, Any]) -> str:
    return str(raw.get("id") or "")


def list_mappings(
    *,
    framework_id: str | None = None,
    framework_version: str | None = None,
    relation: str | None = None,
    review: str | None = None,
) -> list[MappingRecord]:
    rows = [_to_record(r) for r in _load().get("mappings") or []]
    if framework_id:
        rows = [m for m in rows if m.framework_id == framework_id]
    if framework_version:
        rows = [m for m in rows if m.framework_version == framework_version]
    if relation:
        rows = [m for m in rows if m.relation.value == relation.upper()]
    if review:
        rows = [m for m in rows if m.review_status.value == review.upper()]
    return rows


def list_mapping_rows(
    *,
    framework_id: str | None = None,
    framework_version: str | None = None,
) -> list[dict[str, Any]]:
    rows = list(_load().get("mappings") or [])
    if framework_id:
        rows = [r for r in rows if str(r.get("framework_id")) == framework_id]
    if framework_version:
        rows = [r for r in rows if str(r.get("framework_version")) == framework_version]
    return rows


def get_mapping(mapping_id: str) -> tuple[str, MappingRecord] | None:
    for raw in _load().get("mappings") or []:
        if _row_id(raw) == mapping_id:
            return mapping_id, _to_record(raw)
    return None


def _assert_version_editable(framework_id: str, framework_version: str) -> None:
    """Published FrameworkVersion mappings are read-only at store level."""
    from engine.framework_versions import VersionStatus, list_versions

    for ver in list_versions(framework_id=framework_id):
        if str(ver.version) == str(framework_version) and ver.status == VersionStatus.PUBLISHED.value:
            raise PermissionError("published_mapping_immutable")


def upsert_mapping(
    record: MappingRecord,
    *,
    mapping_id: str | None = None,
) -> tuple[str, MappingRecord]:
    if record.relation == CoverageRelation.PARTIAL and not (record.uncovered_delta or "").strip():
        raise ValueError("partial_requires_delta")
    _assert_version_editable(record.framework_id, record.framework_version)
    data = _load()
    rows = list(data.get("mappings") or [])
    payload = {
        "id": mapping_id or f"map-{secrets.token_hex(6)}",
        "requirement_id": record.requirement_id,
        "framework_id": record.framework_id,
        "framework_name": record.framework_name,
        "framework_version": record.framework_version,
        "requirement_code": record.requirement_code,
        "canonical_control_id": record.canonical_control_id,
        "canonical_control_ref": record.canonical_control_ref,
        "relation": record.relation.value,
        "rationale": record.rationale,
        "uncovered_delta": record.uncovered_delta,
        "notes": record.notes,
        "confidence": record.confidence,
        "review_status": record.review_status.value,
    }
    # Replace by id or by requirement+control identity
    found = False
    for i, row in enumerate(rows):
        same_id = mapping_id and _row_id(row) == mapping_id
        same_pair = (
            str(row.get("requirement_id")) == record.requirement_id
            and str(row.get("canonical_control_ref")) == record.canonical_control_ref
            and str(row.get("framework_version")) == record.framework_version
        )
        if same_id or same_pair:
            payload["id"] = _row_id(row) or payload["id"]
            rows[i] = payload
            found = True
            break
    if not found:
        rows.append(payload)
    data["mappings"] = rows
    _save(data)
    return payload["id"], _to_record(payload)


def delete_mapping(mapping_id: str) -> bool:
    data = _load()
    rows = list(data.get("mappings") or [])
    new_rows = [r for r in rows if _row_id(r) != mapping_id]
    if len(new_rows) == len(rows):
        return False
    data["mappings"] = new_rows
    _save(data)
    return True


def seed_from_programs(programs: list[Any]) -> int:
    """Copy program mappings into KB store (idempotent by requirement+control+version)."""
    existing = {
        (
            str(r.get("requirement_id")),
            str(r.get("canonical_control_ref")),
            str(r.get("framework_version")),
        )
        for r in _load().get("mappings") or []
    }
    added = 0
    for program in programs:
        for m in getattr(program, "mappings", []) or []:
            key = (m.requirement_id, m.canonical_control_ref, m.framework_version)
            if key in existing:
                continue
            upsert_mapping(m)
            existing.add(key)
            added += 1
    return added


def coverage_summary(
    requirements: list[Any],
    mappings: list[MappingRecord],
) -> dict[str, Any]:
    mapped_ids = {m.requirement_id for m in mappings}
    by_rel = {"FULL": 0, "PARTIAL": 0, "SUPPORTING": 0}
    for m in mappings:
        by_rel[m.relation.value] = by_rel.get(m.relation.value, 0) + 1
    leafs = [r for r in requirements if getattr(r, "is_leaf", True)]
    total = len(leafs) if leafs else len(requirements)
    unmapped = [r for r in (leafs or requirements) if getattr(r, "id", None) not in mapped_ids]
    return {
        "total_requirements": total,
        "full": by_rel.get("FULL", 0),
        "partial": by_rel.get("PARTIAL", 0),
        "supporting": by_rel.get("SUPPORTING", 0),
        "unmapped": len(unmapped),
        "unmapped_items": unmapped,
        "mapped": total - len(unmapped),
    }


__all__ = [
    "list_mappings",
    "list_mapping_rows",
    "get_mapping",
    "upsert_mapping",
    "delete_mapping",
    "seed_from_programs",
    "coverage_summary",
    "store_path",
]

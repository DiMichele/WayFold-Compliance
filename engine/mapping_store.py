from __future__ import annotations

import json
from pathlib import Path

from .domain import CoverageRelation, MappingRecord, ReviewStatus


def load_mappings(path: Path) -> list[MappingRecord]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw["mappings"] if isinstance(raw, dict) else raw
    out: list[MappingRecord] = []
    for item in items:
        out.append(
            MappingRecord(
                requirement_id=item["requirement_id"],
                framework_id=item["framework_id"],
                framework_name=item["framework_name"],
                framework_version=str(item.get("framework_version", "")),
                requirement_code=item["requirement_code"],
                canonical_control_id=item["canonical_control_id"],
                canonical_control_ref=item["canonical_control_ref"],
                relation=CoverageRelation(item["relation"]),
                rationale=item.get("rationale", ""),
                uncovered_delta=item.get("uncovered_delta", ""),
                notes=item.get("notes", ""),
                confidence=item.get("confidence"),
                review_status=ReviewStatus(item.get("review_status", "APPROVED")),
            )
        )
    return out


def save_mappings(path: Path, mappings: list[MappingRecord]) -> None:
    payload = {
        "mappings": [
            {
                "requirement_id": m.requirement_id,
                "framework_id": m.framework_id,
                "framework_name": m.framework_name,
                "framework_version": m.framework_version,
                "requirement_code": m.requirement_code,
                "canonical_control_id": m.canonical_control_id,
                "canonical_control_ref": m.canonical_control_ref,
                "relation": m.relation.value,
                "rationale": m.rationale,
                "uncovered_delta": m.uncovered_delta,
                "notes": m.notes,
                "confidence": m.confidence,
                "review_status": m.review_status.value,
            }
            for m in mappings
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

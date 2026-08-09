"""Persistent assessment report snapshots (historical, not live DB views)."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from engine.domain import ProgramSnapshot
from engine.runtime_paths import data_root

DISCLAIMER_IT = (
    "Lo stato indicato rappresenta una valutazione dell'implementazione rispetto "
    "ai requisiti configurati nel programma e non costituisce certificazione "
    "o attestazione legale di conformità."
)


@dataclass
class ReportSnapshot:
    id: str
    tenant_id: str
    tenant_name: str
    program_id: str
    program_name: str
    scope: str
    assessment_date: str
    generated_at: str
    generated_by: str
    framework_baselines: list[dict[str, str]]
    readiness: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    unmapped: list[dict[str, Any]]
    implementation_summary: dict[str, Any]
    remediation: list[dict[str, Any]]
    disclaimer: str = DISCLAIMER_IT
    dataset_marker: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


def snapshots_root() -> Path:
    root = data_root() / "report_snapshots"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _index_path() -> Path:
    return snapshots_root() / "index.json"


def _load_index() -> dict[str, Any]:
    path = _index_path()
    if not path.is_file():
        return {"items": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": []}


def _save_index(data: dict[str, Any]) -> None:
    path = _index_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def generate_snapshot(
    program: ProgramSnapshot,
    *,
    generated_by: str,
    as_of: date | None = None,
) -> ReportSnapshot:
    from engine.reports import DISCLAIMER_IT as _DISC
    from engine.reports import build_report_context

    ctx = build_report_context(program, as_of=as_of)
    disclaimer = str(ctx.get("disclaimer") or _DISC)
    baselines = []
    for row in ctx["readiness"]:
        baselines.append(
            {
                "framework_id": row.framework_id,
                "framework_name": row.framework_name,
                "framework_version": row.framework_version,
                "implementation_readiness": row.implementation_readiness,
            }
        )
    gaps = [
        {
            "framework": g.framework_name,
            "version": g.framework_version,
            "requirement": g.requirement_code,
            "control": g.canonical_control_ref,
            "mapping": g.mapping,
            "status": g.status,
            "gap": g.gap,
            "owner": g.owner,
            "deadline": g.deadline,
            "priority": g.priority,
        }
        for g in ctx["gaps"]
    ]
    unmapped = [
        {
            "framework": u.framework_name,
            "version": u.framework_version,
            "code": u.code,
            "title": u.title,
        }
        for u in ctx["unmapped"]
    ]
    remediation = [
        {
            "ref": str(getattr(item, "control_ref", None) or getattr(item, "name", "")),
            "due_date": getattr(item, "due_date", None),
            "owner": getattr(item, "owner", None),
            "overdue": bool(getattr(item, "overdue", False)),
        }
        for item in ctx["overdue_tasks"]
    ]
    snap = ReportSnapshot(
        id=f"rpt-{secrets.token_hex(6)}",
        tenant_id=program.tenant_id,
        tenant_name=program.tenant_name,
        program_id=program.program_id,
        program_name=program.program_name,
        scope=program.scope or ctx["scope"],
        assessment_date=ctx["assessment_date"],
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        generated_by=generated_by,
        framework_baselines=baselines,
        readiness=[
            {
                "framework_name": r.framework_name,
                "framework_version": r.framework_version,
                "fully_covered": r.fully_covered,
                "partially_covered": r.partially_covered,
                "not_covered": r.not_covered,
                "unmapped": r.unmapped,
                "not_applicable": r.not_applicable,
                "implementation_readiness": r.implementation_readiness,
            }
            for r in ctx["readiness"]
        ],
        gaps=gaps,
        unmapped=unmapped,
        implementation_summary={
            "unified_controls": ctx["checklist"].unified_control_count,
            "raw_requirements": ctx["checklist"].raw_requirement_count,
            "in_progress": len(ctx["in_progress"]),
            "critical_gaps": len(ctx["critical_gaps"]),
            "high_priority_gaps": len(ctx["high_priority_gaps"]),
        },
        remediation=remediation,
        disclaimer=disclaimer,
        dataset_marker=getattr(program, "dataset_marker", "") or "",
    )
    path = snapshots_root() / f"{snap.id}.json"
    path.write_text(json.dumps(asdict(snap), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    idx = _load_index()
    items = list(idx.get("items") or [])
    items.insert(
        0,
        {
            "id": snap.id,
            "tenant_id": snap.tenant_id,
            "program_id": snap.program_id,
            "program_name": snap.program_name,
            "generated_at": snap.generated_at,
            "generated_by": snap.generated_by,
            "assessment_date": snap.assessment_date,
            "baselines": [
                f"{b['framework_name']}@{b['framework_version']}" for b in snap.framework_baselines
            ],
        },
    )
    idx["items"] = items[:500]
    _save_index(idx)
    return snap


def get_snapshot(snapshot_id: str) -> ReportSnapshot | None:
    path = snapshots_root() / f"{snapshot_id}.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return ReportSnapshot(**raw)


def list_snapshots(
    *,
    tenant_id: str | None = None,
    program_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    items = list(_load_index().get("items") or [])
    if tenant_id:
        items = [i for i in items if i.get("tenant_id") == tenant_id]
    if program_id:
        items = [i for i in items if i.get("program_id") == program_id]
    return items[:limit]

"""Canonical / unified control catalog (Knowledge Base).

Controls are framework-agnostic. Framework linkage happens via MappingRecord.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.runtime_paths import data_root


@dataclass
class CanonicalControl:
    id: str
    code: str
    title: str
    domain: str = ""
    objective: str = ""
    description: str = ""
    implementation_guidance: str = ""
    suggested_evidence: str = ""
    default_priority: str = "MEDIUM"
    status: str = "ACTIVE"
    created_at: str = ""
    updated_at: str = ""


def store_path() -> Path:
    return data_root() / "control_catalog.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load() -> dict[str, Any]:
    path = store_path()
    if not path.is_file():
        return {"controls": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"controls": []}


def _save(data: dict[str, Any]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _from_raw(raw: dict[str, Any]) -> CanonicalControl:
    return CanonicalControl(
        id=str(raw.get("id") or ""),
        code=str(raw.get("code") or ""),
        title=str(raw.get("title") or ""),
        domain=str(raw.get("domain") or ""),
        objective=str(raw.get("objective") or ""),
        description=str(raw.get("description") or ""),
        implementation_guidance=str(raw.get("implementation_guidance") or ""),
        suggested_evidence=str(raw.get("suggested_evidence") or ""),
        default_priority=str(raw.get("default_priority") or "MEDIUM"),
        status=str(raw.get("status") or "ACTIVE"),
        created_at=str(raw.get("created_at") or ""),
        updated_at=str(raw.get("updated_at") or ""),
    )


def list_controls(*, status: str | None = None, q: str | None = None) -> list[CanonicalControl]:
    rows = [_from_raw(r) for r in _load().get("controls") or []]
    if status:
        rows = [c for c in rows if c.status.upper() == status.upper()]
    if q:
        needle = q.strip().lower()
        rows = [
            c
            for c in rows
            if needle in c.code.lower()
            or needle in c.title.lower()
            or needle in c.domain.lower()
            or needle in c.description.lower()
        ]
    rows.sort(key=lambda c: c.code)
    return rows


def get_control(control_id: str) -> CanonicalControl | None:
    for c in list_controls():
        if c.id == control_id or c.code == control_id:
            return c
    return None


def get_by_code(code: str) -> CanonicalControl | None:
    code_u = code.strip().upper()
    for c in list_controls():
        if c.code.upper() == code_u:
            return c
    return None


def upsert_control(control: CanonicalControl) -> CanonicalControl:
    data = _load()
    rows = list(data.get("controls") or [])
    payload = asdict(control)
    found = False
    for i, row in enumerate(rows):
        if str(row.get("id")) == control.id or str(row.get("code", "")).upper() == control.code.upper():
            payload["id"] = str(row.get("id") or control.id)
            payload["created_at"] = str(row.get("created_at") or control.created_at or _now())
            payload["updated_at"] = _now()
            rows[i] = payload
            found = True
            control = _from_raw(payload)
            break
    if not found:
        if not control.id:
            control.id = f"ctrl-{secrets.token_hex(6)}"
        if not control.created_at:
            control.created_at = _now()
        control.updated_at = _now()
        rows.append(asdict(control))
    data["controls"] = rows
    _save(data)
    return control


def create_control(
    *,
    code: str,
    title: str,
    domain: str = "",
    objective: str = "",
    description: str = "",
    implementation_guidance: str = "",
    suggested_evidence: str = "",
    default_priority: str = "MEDIUM",
    status: str = "ACTIVE",
) -> CanonicalControl:
    code = code.strip()
    if not code:
        raise ValueError("code_required")
    if not title.strip():
        raise ValueError("title_required")
    if get_by_code(code):
        raise ValueError("duplicate_control_code")
    return upsert_control(
        CanonicalControl(
            id=f"ctrl-{secrets.token_hex(6)}",
            code=code,
            title=title.strip(),
            domain=domain.strip(),
            objective=objective.strip(),
            description=description.strip(),
            implementation_guidance=implementation_guidance.strip(),
            suggested_evidence=suggested_evidence.strip(),
            default_priority=(default_priority or "MEDIUM").upper(),
            status=(status or "ACTIVE").upper(),
            created_at=_now(),
            updated_at=_now(),
        )
    )


def seed_from_programs(programs: list[Any]) -> list[CanonicalControl]:
    """Idempotent bootstrap of catalog entries from program implementations/mappings."""
    existing = {c.code.upper(): c for c in list_controls()}
    created: list[CanonicalControl] = []
    for program in programs:
        seen: set[str] = set()
        for impl in getattr(program, "implementations", []) or []:
            ref = (impl.canonical_control_ref or impl.ref_id or "").strip()
            if not ref or ref.upper() in seen or ref.upper() in existing:
                continue
            seen.add(ref.upper())
            ctrl = create_control(
                code=ref,
                title=impl.name or ref,
                domain=_domain_from_code(ref),
                description=getattr(impl, "description", "") or "",
                default_priority=(impl.priority or "MEDIUM"),
            )
            existing[ref.upper()] = ctrl
            created.append(ctrl)
        for m in getattr(program, "mappings", []) or []:
            ref = (m.canonical_control_ref or "").strip()
            if not ref or ref.upper() in seen or ref.upper() in existing:
                continue
            seen.add(ref.upper())
            ctrl = create_control(
                code=ref,
                title=ref,
                domain=_domain_from_code(ref),
            )
            existing[ref.upper()] = ctrl
            created.append(ctrl)
    return created


def _domain_from_code(code: str) -> str:
    u = code.upper()
    if "IAM" in u or "ACCESS" in u:
        return "Accesso"
    if "IR" in u or "INCIDENT" in u:
        return "Incidenti"
    if "LOG" in u:
        return "Logging"
    if "ENC" in u or "CRYPTO" in u:
        return "Crittografia"
    if "BCP" in u or "BC" in u:
        return "Continuità"
    if "GOV" in u:
        return "Governance"
    if "SUP" in u:
        return "Fornitori"
    return "Generale"


__all__ = [
    "CanonicalControl",
    "list_controls",
    "get_control",
    "get_by_code",
    "upsert_control",
    "create_control",
    "seed_from_programs",
    "store_path",
]

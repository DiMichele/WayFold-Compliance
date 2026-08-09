"""Framework version registry with published immutability.

Published versions cannot be edited in-place. Workflow:
Published → clone draft → edit → review → publish.
"""

from __future__ import annotations

import copy
import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from engine.runtime_paths import data_root


class VersionStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    RETIRED = "RETIRED"


@dataclass
class FrameworkRequirement:
    id: str
    code: str
    title: str
    parent_id: str | None = None
    section: str = ""
    source_url: str = ""
    order: int = 0
    description: str = ""
    req_type: str = "Requisito"  # Requisito | Articolo | Misura | Controllo normativo
    source_reference: str = ""
    conditions: str = ""
    frequency: str = ""
    is_leaf: bool = True


@dataclass
class FrameworkVersionRecord:
    id: str
    framework_id: str
    framework_name: str
    publisher: str
    version: str
    status: str
    requirements: list[FrameworkRequirement] = field(default_factory=list)
    effective_date: str | None = None
    publication_date: str | None = None
    notes: str = ""
    source_url: str = ""
    cloned_from: str | None = None
    created_at: str = ""
    published_at: str | None = None


class ImmutabilityError(PermissionError):
    pass


def store_path() -> Path:
    return data_root() / "framework_versions.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load() -> dict[str, Any]:
    path = store_path()
    if not path.is_file():
        return {"versions": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"versions": []}


def _save(data: dict[str, Any]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _req_from(raw: dict[str, Any]) -> FrameworkRequirement:
    parent = raw.get("parent_id")
    if parent is not None:
        parent = str(parent) or None
    return FrameworkRequirement(
        id=str(raw.get("id") or ""),
        code=str(raw.get("code") or ""),
        title=str(raw.get("title") or ""),
        parent_id=parent,
        section=str(raw.get("section") or ""),
        source_url=str(raw.get("source_url") or ""),
        order=int(raw.get("order") or 0),
        description=str(raw.get("description") or ""),
        req_type=str(raw.get("req_type") or raw.get("type") or "Requisito"),
        source_reference=str(raw.get("source_reference") or ""),
        conditions=str(raw.get("conditions") or ""),
        frequency=str(raw.get("frequency") or ""),
        is_leaf=bool(raw.get("is_leaf", True)),
    )


def _ver_from(raw: dict[str, Any]) -> FrameworkVersionRecord:
    return FrameworkVersionRecord(
        id=str(raw["id"]),
        framework_id=str(raw.get("framework_id") or ""),
        framework_name=str(raw.get("framework_name") or ""),
        publisher=str(raw.get("publisher") or ""),
        version=str(raw.get("version") or ""),
        status=str(raw.get("status") or VersionStatus.DRAFT.value),
        requirements=[_req_from(r) for r in raw.get("requirements") or []],
        effective_date=raw.get("effective_date"),
        publication_date=raw.get("publication_date"),
        notes=str(raw.get("notes") or ""),
        source_url=str(raw.get("source_url") or ""),
        cloned_from=raw.get("cloned_from"),
        created_at=str(raw.get("created_at") or ""),
        published_at=raw.get("published_at"),
    )


def list_versions(*, framework_id: str | None = None) -> list[FrameworkVersionRecord]:
    versions = [_ver_from(r) for r in _load().get("versions", [])]
    if framework_id:
        versions = [v for v in versions if v.framework_id == framework_id]
    versions.sort(key=lambda v: (v.framework_name, v.version), reverse=True)
    return versions


def get_version(version_id: str) -> FrameworkVersionRecord | None:
    for v in list_versions():
        if v.id == version_id:
            return v
    return None


def upsert_version(record: FrameworkVersionRecord, *, force: bool = False) -> FrameworkVersionRecord:
    existing = get_version(record.id)
    if existing and existing.status == VersionStatus.PUBLISHED.value and not force:
        raise ImmutabilityError("published_version_immutable")
    data = _load()
    rows = list(data.get("versions") or [])
    payload = asdict(record)
    found = False
    for i, row in enumerate(rows):
        if str(row.get("id")) == record.id:
            rows[i] = payload
            found = True
            break
    if not found:
        rows.append(payload)
    data["versions"] = rows
    _save(data)
    return record


def update_published_denied(version_id: str, patch: dict[str, Any]) -> None:
    """API-facing guard: PATCH on published → always denied."""
    ver = get_version(version_id)
    if ver is None:
        raise KeyError(version_id)
    if ver.status == VersionStatus.PUBLISHED.value:
        raise ImmutabilityError("published_version_immutable")
    for key, value in patch.items():
        if key == "requirements":
            ver.requirements = [_req_from(r) if isinstance(r, dict) else r for r in value]
        elif hasattr(ver, key) and key not in {"id", "status"}:
            setattr(ver, key, value)
    upsert_version(ver)


def update_requirement(version_id: str, requirement_id: str, patch: dict[str, Any]) -> FrameworkRequirement:
    ver = get_version(version_id)
    if ver is None:
        raise KeyError(version_id)
    if ver.status == VersionStatus.PUBLISHED.value:
        raise ImmutabilityError("published_requirement_immutable")
    for req in ver.requirements:
        if req.id == requirement_id:
            for key, value in patch.items():
                if hasattr(req, key) and key != "id":
                    setattr(req, key, value)
            upsert_version(ver)
            return req
    raise KeyError(requirement_id)


def create_version(
    *,
    framework_id: str,
    framework_name: str,
    publisher: str = "",
    version: str,
    notes: str = "",
    effective_date: str | None = None,
    publication_date: str | None = None,
    source_url: str = "",
    status: str = "DRAFT",
) -> FrameworkVersionRecord:
    version = (version or "").strip()
    if not framework_id or not version:
        raise ValueError("framework_id_and_version_required")
    for existing in list_versions(framework_id=framework_id):
        if existing.version == version:
            raise ValueError("duplicate_version_label")
    rec = FrameworkVersionRecord(
        id=f"fv-{secrets.token_hex(6)}",
        framework_id=framework_id,
        framework_name=framework_name,
        publisher=publisher,
        version=version,
        status=VersionStatus.DRAFT.value if status != VersionStatus.PUBLISHED.value else VersionStatus.DRAFT.value,
        requirements=[],
        effective_date=effective_date or None,
        publication_date=publication_date or None,
        notes=notes or "",
        source_url=source_url or "",
        created_at=_now(),
    )
    return upsert_version(rec)


def add_requirement(
    version_id: str,
    *,
    code: str,
    title: str,
    description: str = "",
    req_type: str = "Requisito",
    section: str = "",
    parent_id: str | None = None,
    parent_code: str | None = None,
    order: int | None = None,
    source_reference: str = "",
    conditions: str = "",
    frequency: str = "",
    source_url: str = "",
    is_leaf: bool = True,
) -> FrameworkRequirement:
    ver = get_version(version_id)
    if ver is None:
        raise KeyError(version_id)
    if ver.status == VersionStatus.PUBLISHED.value:
        raise ImmutabilityError("published_requirement_immutable")
    code = code.strip()
    title = title.strip()
    if not code or not title:
        raise ValueError("code_and_title_required")
    if any(r.code == code for r in ver.requirements):
        raise ValueError("duplicate_requirement_code")
    resolved_parent = parent_id
    if not resolved_parent and parent_code:
        for r in ver.requirements:
            if r.code == parent_code:
                resolved_parent = r.id
                r.is_leaf = False
                break
    req = FrameworkRequirement(
        id=f"req-{secrets.token_hex(6)}",
        code=code,
        title=title,
        parent_id=resolved_parent,
        section=section,
        source_url=source_url,
        order=len(ver.requirements) if order is None else int(order),
        description=description,
        req_type=req_type or "Requisito",
        source_reference=source_reference,
        conditions=conditions,
        frequency=frequency,
        is_leaf=is_leaf,
    )
    ver.requirements.append(req)
    upsert_version(ver)
    return req


def import_requirements_csv(
    version_id: str,
    csv_text: str,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    """Preview or apply CSV import. Never partially applies on validation errors."""
    import csv
    import io

    ver = get_version(version_id)
    if ver is None:
        raise KeyError(version_id)
    if ver.status == VersionStatus.PUBLISHED.value:
        raise ImmutabilityError("published_requirement_immutable")

    reader = csv.DictReader(io.StringIO(csv_text))
    required_cols = {"code", "title"}
    if not reader.fieldnames or not required_cols.issubset({c.strip() for c in reader.fieldnames}):
        raise ValueError("csv_missing_columns")

    existing_by_code = {r.code: r for r in ver.requirements}
    news: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for i, row in enumerate(reader, start=2):
        code = (row.get("code") or "").strip()
        title = (row.get("title") or "").strip()
        if not code or not title:
            errors.append({"line": i, "error": "code_and_title_required", "code": code})
            continue
        if code in seen_codes:
            errors.append({"line": i, "error": "duplicate_in_file", "code": code})
            continue
        seen_codes.add(code)
        payload = {
            "code": code,
            "title": title,
            "description": (row.get("description") or "").strip(),
            "req_type": (row.get("type") or row.get("req_type") or "Requisito").strip(),
            "section": (row.get("section") or "").strip(),
            "parent_code": (row.get("parent_code") or "").strip() or None,
            "order": int(row.get("order") or 0) if (row.get("order") or "").strip() else None,
            "source_reference": (row.get("source_reference") or "").strip(),
        }
        if code in existing_by_code:
            updates.append(payload)
        else:
            news.append(payload)

    # Validate parent_code references
    known = set(existing_by_code) | {r["code"] for r in news} | {r["code"] for r in updates}
    for payload in news + updates:
        pc = payload.get("parent_code")
        if pc and pc not in known:
            errors.append({"line": 0, "error": "unknown_parent_code", "code": payload["code"], "parent_code": pc})

    result = {
        "new": news,
        "updates": updates,
        "errors": errors,
        "can_apply": not errors,
        "applied": False,
    }
    if not apply or errors:
        return result

    for payload in updates:
        req = existing_by_code[payload["code"]]
        patch = {
            "title": payload["title"],
            "description": payload["description"],
            "req_type": payload["req_type"],
            "section": payload["section"],
            "source_reference": payload["source_reference"],
        }
        if payload["order"] is not None:
            patch["order"] = payload["order"]
        if payload.get("parent_code"):
            for r in ver.requirements:
                if r.code == payload["parent_code"]:
                    patch["parent_id"] = r.id
                    r.is_leaf = False
                    break
        update_requirement(version_id, req.id, patch)

    for payload in news:
        add_requirement(
            version_id,
            code=payload["code"],
            title=payload["title"],
            description=payload["description"],
            req_type=payload["req_type"],
            section=payload["section"],
            parent_code=payload.get("parent_code"),
            order=payload.get("order"),
            source_reference=payload["source_reference"],
        )
    result["applied"] = True
    return result


CSV_TEMPLATE = """code,title,description,type,section,parent_code,order,source_reference
XYZ-01,Gestione degli accessi,Descrizione esempio,Requisito,Accesso,,10,Art. 1
XYZ-01.1,Autenticazione,Sotto-voce,Requisito,Accesso,XYZ-01,11,Art. 1.1
"""


def clone_draft(version_id: str, *, new_version: str) -> FrameworkVersionRecord:
    src = get_version(version_id)
    if src is None:
        raise KeyError(version_id)
    draft = FrameworkVersionRecord(
        id=f"fv-{secrets.token_hex(6)}",
        framework_id=src.framework_id,
        framework_name=src.framework_name,
        publisher=src.publisher,
        version=new_version,
        status=VersionStatus.DRAFT.value,
        requirements=copy.deepcopy(src.requirements),
        effective_date=None,
        publication_date=None,
        notes=src.notes,
        source_url=src.source_url,
        cloned_from=src.id,
        created_at=_now(),
        published_at=None,
    )
    return upsert_version(draft)


def publish_version(version_id: str) -> FrameworkVersionRecord:
    ver = get_version(version_id)
    if ver is None:
        raise KeyError(version_id)
    if ver.status == VersionStatus.PUBLISHED.value:
        return ver
    # Retire previous published for same framework
    for other in list_versions(framework_id=ver.framework_id):
        if other.id != ver.id and other.status == VersionStatus.PUBLISHED.value:
            other.status = VersionStatus.RETIRED.value
            upsert_version(other, force=True)
    ver.status = VersionStatus.PUBLISHED.value
    ver.published_at = _now()
    return upsert_version(ver, force=True)


def seed_from_programs(programs: list[Any]) -> list[FrameworkVersionRecord]:
    """Bootstrap KB versions from demo program snapshots (idempotent by framework+version)."""
    from engine.framework_registry import ensure_from_version

    existing = {(v.framework_id, v.version): v for v in list_versions()}
    created: list[FrameworkVersionRecord] = []
    for program in programs:
        seen_fw: set[tuple[str, str]] = set()
        for req in program.requirements:
            key = (req.framework_id, req.framework_version)
            if key in seen_fw:
                continue
            seen_fw.add(key)
            ensure_from_version(
                framework_id=req.framework_id,
                framework_name=req.framework_name,
                publisher=_publisher_for(req.framework_name),
            )
            if key in existing:
                continue
            reqs = [
                FrameworkRequirement(
                    id=r.id,
                    code=r.code,
                    title=r.title,
                    parent_id=_infer_parent(r.code),
                    section=r.code.split(".")[0] if "." in r.code else r.code[:3],
                    order=i,
                    is_leaf=bool(getattr(r, "is_leaf", True)),
                )
                for i, r in enumerate(
                    x
                    for x in program.requirements
                    if x.framework_id == req.framework_id
                    and x.framework_version == req.framework_version
                )
            ]
            rec = FrameworkVersionRecord(
                id=f"fv-{req.framework_id}-{req.framework_version}".replace(" ", "_"),
                framework_id=req.framework_id,
                framework_name=req.framework_name,
                publisher=_publisher_for(req.framework_name),
                version=req.framework_version,
                status=VersionStatus.PUBLISHED.value,
                requirements=reqs,
                created_at=_now(),
                published_at=_now(),
            )
            upsert_version(rec, force=True)
            existing[key] = rec
            created.append(rec)
        for avail in getattr(program, "available_framework_versions", []) or []:
            # Prefer same framework family id as pinned baseline when notes indicate successor.
            fw_id = str(avail.get("framework_id") or "")
            ver = str(avail.get("version") or avail.get("framework_version") or "")
            status = str(avail.get("status") or VersionStatus.DRAFT.value)
            name = str(avail.get("framework_name") or fw_id)
            if not fw_id or not ver:
                continue
            # Normalize mistaken version-suffixed ids (fw-nis2-it-2026-2 → fw-nis2-it-2026-1 family)
            canonical_fw = fw_id
            for pinned_fw, pinned_ver in seen_fw:
                if name and name == next(
                    (r.framework_name for r in program.requirements if r.framework_id == pinned_fw),
                    None,
                ):
                    # Same display name → same framework_id family
                    if pinned_fw.rsplit("-", 1)[0] in fw_id or fw_id.startswith(pinned_fw.rsplit("-", 1)[0]):
                        canonical_fw = pinned_fw
                        break
            ensure_from_version(
                framework_id=canonical_fw,
                framework_name=name,
                publisher=_publisher_for(name),
            )
            key = (canonical_fw, ver)
            if key in existing:
                continue
            # Clone requirements from latest published of same framework when draft empty
            base_reqs: list[FrameworkRequirement] = []
            published = [
                v
                for v in list_versions(framework_id=canonical_fw)
                if v.status == VersionStatus.PUBLISHED.value
            ]
            if published:
                base_reqs = copy.deepcopy(published[0].requirements)
            rec = FrameworkVersionRecord(
                id=f"fv-{canonical_fw}-{ver}".replace(" ", "_"),
                framework_id=canonical_fw,
                framework_name=name,
                publisher=_publisher_for(name),
                version=ver,
                status=status,
                requirements=base_reqs,
                created_at=_now(),
            )
            upsert_version(rec, force=True)
            existing[key] = rec
            created.append(rec)
    return created


def _infer_parent(code: str) -> str | None:
    if "." not in code:
        return None
    parts = code.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def _publisher_for(name: str) -> str:
    n = name.lower()
    if "nis2" in n:
        return "ACN / UE"
    if "iso" in n:
        return "ISO/IEC"
    if "psnc" in n:
        return "ACN"
    if "dora" in n:
        return "UE"
    return "Publisher"


def diff_versions(from_id: str, to_id: str) -> dict[str, Any]:
    a = get_version(from_id)
    b = get_version(to_id)
    if a is None or b is None:
        raise KeyError("version_not_found")
    a_map = {r.code: r for r in a.requirements}
    b_map = {r.code: r for r in b.requirements}
    added = [asdict(b_map[c]) for c in b_map if c not in a_map]
    removed = [asdict(a_map[c]) for c in a_map if c not in b_map]
    modified = []
    for code in a_map:
        if code in b_map and (
            a_map[code].title != b_map[code].title
            or a_map[code].section != b_map[code].section
        ):
            modified.append({"from": asdict(a_map[code]), "to": asdict(b_map[code])})
    return {
        "from": {"id": a.id, "version": a.version, "status": a.status},
        "to": {"id": b.id, "version": b.version, "status": b.status},
        "added": added,
        "removed": removed,
        "modified": modified,
        "mapping_changes": [],  # filled by caller when program mappings available
        "client_impact_note": (
            "I programmi con baseline bloccata sulla versione precedente "
            "non vengono aggiornati automaticamente."
        ),
    }

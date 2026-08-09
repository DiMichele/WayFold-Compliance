"""Framework / Normativa registry (metadata separate from version packages)."""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.runtime_paths import data_root

FRAMEWORK_TYPES = (
    "Standard",
    "Normativa",
    "Regolamento",
    "Schema",
    "Framework",
    "Linea guida",
)


@dataclass
class FrameworkRecord:
    id: str
    name: str
    short_name: str = ""
    type: str = "Framework"
    publisher: str = ""
    jurisdiction: str = ""
    language: str = "it"
    description: str = ""
    official_url: str = ""
    created_at: str = ""


def store_path() -> Path:
    return data_root() / "framework_registry.json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load() -> dict[str, Any]:
    path = store_path()
    if not path.is_file():
        return {"frameworks": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"frameworks": []}


def _save(data: dict[str, Any]) -> None:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _from_raw(raw: dict[str, Any]) -> FrameworkRecord:
    return FrameworkRecord(
        id=str(raw.get("id") or ""),
        name=str(raw.get("name") or ""),
        short_name=str(raw.get("short_name") or ""),
        type=str(raw.get("type") or "Framework"),
        publisher=str(raw.get("publisher") or ""),
        jurisdiction=str(raw.get("jurisdiction") or ""),
        language=str(raw.get("language") or "it"),
        description=str(raw.get("description") or ""),
        official_url=str(raw.get("official_url") or ""),
        created_at=str(raw.get("created_at") or ""),
    )


def list_frameworks() -> list[FrameworkRecord]:
    rows = [_from_raw(r) for r in _load().get("frameworks") or []]
    rows.sort(key=lambda f: f.name.lower())
    return rows


def get_framework(framework_id: str) -> FrameworkRecord | None:
    for f in list_frameworks():
        if f.id == framework_id:
            return f
    return None


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s[:48] or secrets.token_hex(4)


def create_framework(
    *,
    name: str,
    short_name: str = "",
    type: str = "Framework",
    publisher: str = "",
    jurisdiction: str = "",
    language: str = "it",
    description: str = "",
    official_url: str = "",
    framework_id: str | None = None,
) -> FrameworkRecord:
    name = name.strip()
    if not name:
        raise ValueError("name_required")
    fw_type = type if type in FRAMEWORK_TYPES else "Framework"
    rec = FrameworkRecord(
        id=framework_id or f"fw-{_slug(short_name or name)}-{secrets.token_hex(3)}",
        name=name,
        short_name=(short_name or name).strip(),
        type=fw_type,
        publisher=publisher.strip(),
        jurisdiction=jurisdiction.strip(),
        language=(language or "it").strip()[:8],
        description=description.strip(),
        official_url=official_url.strip(),
        created_at=_now(),
    )
    data = _load()
    rows = list(data.get("frameworks") or [])
    if any(str(r.get("id")) == rec.id for r in rows):
        raise ValueError("duplicate_framework_id")
    rows.append(asdict(rec))
    data["frameworks"] = rows
    _save(data)
    return rec


def upsert_framework(rec: FrameworkRecord) -> FrameworkRecord:
    data = _load()
    rows = list(data.get("frameworks") or [])
    payload = asdict(rec)
    found = False
    for i, row in enumerate(rows):
        if str(row.get("id")) == rec.id:
            payload["created_at"] = str(row.get("created_at") or rec.created_at or _now())
            rows[i] = payload
            found = True
            break
    if not found:
        if not payload.get("created_at"):
            payload["created_at"] = _now()
        rows.append(payload)
    data["frameworks"] = rows
    _save(data)
    return _from_raw(payload)


def ensure_from_version(
    *,
    framework_id: str,
    framework_name: str,
    publisher: str = "",
    source_url: str = "",
) -> FrameworkRecord:
    existing = get_framework(framework_id)
    if existing:
        return existing
    return create_framework(
        name=framework_name,
        short_name=framework_name,
        publisher=publisher,
        official_url=source_url,
        framework_id=framework_id,
    )


__all__ = [
    "FRAMEWORK_TYPES",
    "FrameworkRecord",
    "list_frameworks",
    "get_framework",
    "create_framework",
    "upsert_framework",
    "ensure_from_version",
    "store_path",
]

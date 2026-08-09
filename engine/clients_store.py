"""First-class Client store (exists with zero programs).

Interim WayFold store pending migration to CISO Folder (DOMAIN).
Replaces pending_clients.json as source of truth.
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from engine.runtime_paths import data_root


@dataclass
class ClientRecord:
    tenant_id: str
    tenant_name: str
    code: str = ""
    description: str = ""
    contact: str = ""
    status: str = "ACTIVE"
    owner: str = ""


def clients_path() -> Path:
    return data_root() / "clients.json"


def _slug(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return s[:40] or secrets.token_hex(3)


def _load() -> dict[str, Any]:
    path = clients_path()
    if not path.is_file():
        # Migrate legacy pending_clients.json once
        legacy = data_root() / "pending_clients.json"
        if legacy.is_file():
            try:
                rows = json.loads(legacy.read_text(encoding="utf-8")).get("clients") or []
                data = {"clients": rows}
                _save(data)
                return data
            except (OSError, json.JSONDecodeError):
                pass
        return {"clients": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"clients": []}


def _save(data: dict[str, Any]) -> None:
    path = clients_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def list_clients() -> list[ClientRecord]:
    out: list[ClientRecord] = []
    for row in _load().get("clients") or []:
        tid = str(row.get("tenant_id") or "").strip()
        name = str(row.get("tenant_name") or row.get("name") or "").strip()
        if not tid or not name:
            continue
        out.append(
            ClientRecord(
                tenant_id=tid,
                tenant_name=name,
                code=str(row.get("code") or ""),
                description=str(row.get("description") or ""),
                contact=str(row.get("contact") or ""),
                status=str(row.get("status") or "ACTIVE").upper(),
                owner=str(row.get("owner") or ""),
            )
        )
    return out


def get_client(tenant_id: str) -> ClientRecord | None:
    for c in list_clients():
        if c.tenant_id == tenant_id:
            return c
    return None


def upsert_client(client: ClientRecord) -> ClientRecord:
    data = _load()
    rows = list(data.get("clients") or [])
    payload = asdict(client)
    found = False
    for i, row in enumerate(rows):
        if str(row.get("tenant_id")) == client.tenant_id:
            rows[i] = payload
            found = True
            break
    if not found:
        rows.append(payload)
    data["clients"] = rows
    _save(data)
    return client


def create_client(
    *,
    name: str,
    code: str = "",
    description: str = "",
    contact: str = "",
    status: str = "ACTIVE",
    owner: str = "",
) -> ClientRecord:
    name = name.strip()
    if not name:
        raise ValueError("name_required")
    code = (code or _slug(name)).strip()
    tenant_id = f"tenant-{_slug(code)}"
    # Avoid collision
    if get_client(tenant_id):
        tenant_id = f"{tenant_id}-{secrets.token_hex(2)}"
    rec = ClientRecord(
        tenant_id=tenant_id,
        tenant_name=name,
        code=code,
        description=description.strip(),
        contact=contact.strip(),
        status=(status or "ACTIVE").upper(),
        owner=owner.strip(),
    )
    return upsert_client(rec)

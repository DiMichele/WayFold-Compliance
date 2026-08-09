"""Immutable product audit trail (append-only JSONL).

Never records passwords, tokens, file content, or API keys.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.runtime_paths import data_root

_lock = threading.Lock()


# Canonical action names
LOGIN = "LOGIN"
LOGOUT = "LOGOUT"
CLIENT_CREATED = "CLIENT_CREATED"
PROGRAM_CREATED = "PROGRAM_CREATED"
CONTROL_STATUS_CHANGED = "CONTROL_STATUS_CHANGED"
CONTROL_OWNER_CHANGED = "CONTROL_OWNER_CHANGED"
CONTROL_NA_CHANGED = "CONTROL_NA_CHANGED"
EVIDENCE_CREATED = "EVIDENCE_CREATED"
EVIDENCE_DELETED = "EVIDENCE_DELETED"
EVIDENCE_DOWNLOADED = "EVIDENCE_DOWNLOADED"
TASK_CREATED = "TASK_CREATED"
TASK_UPDATED = "TASK_UPDATED"
TASK_COMPLETED = "TASK_COMPLETED"
MAPPING_CREATED = "MAPPING_CREATED"
MAPPING_UPDATED = "MAPPING_UPDATED"
MAPPING_APPROVED = "MAPPING_APPROVED"
MAPPING_REJECTED = "MAPPING_REJECTED"
FRAMEWORK_CREATED = "FRAMEWORK_CREATED"
FRAMEWORK_VERSION_CREATED = "FRAMEWORK_VERSION_CREATED"
FRAMEWORK_VERSION_PUBLISHED = "FRAMEWORK_VERSION_PUBLISHED"
FRAMEWORK_VERSION_CLONE = "FRAMEWORK_VERSION_CLONE"
REQUIREMENT_CREATED = "REQUIREMENT_CREATED"
REQUIREMENT_UPDATED = "REQUIREMENT_UPDATED"
CONTROL_CREATED = "CONTROL_CREATED"
CONTROL_UPDATED = "CONTROL_UPDATED"
AI_PROCESSING_ENABLED = "AI_PROCESSING_ENABLED"
AI_PROCESSING_DISABLED = "AI_PROCESSING_DISABLED"
REPORT_GENERATED = "REPORT_GENERATED"
ACCESS_DENIED = "ACCESS_DENIED"


_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "file_content",
        "content",
        "mfa_secret",
        "recovery_codes",
    }
)


@dataclass
class AuditEvent:
    timestamp: str
    actor_user_id: str
    action: str
    entity_type: str
    entity_id: str
    tenant_id: str | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    detail: str = ""
    request_id: str | None = None
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)


def audit_path() -> Path:
    return data_root() / "audit" / "events.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if str(k).lower() in _SENSITIVE_KEYS:
                out[k] = "[redacted]"
            else:
                out[k] = _scrub(v)
        return out
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def record_event(
    *,
    actor_user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    tenant_id: str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    detail: str = "",
    request_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        timestamp=_now(),
        actor_user_id=actor_user_id or "anonymous",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
        old_value=_scrub(old_value) if old_value else None,
        new_value=_scrub(new_value) if new_value else None,
        detail=detail,
        request_id=request_id,
    )
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(asdict(event), ensure_ascii=False) + "\n"
    with _lock:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
    return event


def list_events(
    *,
    tenant_id: str | None = None,
    actor_user_id: str | None = None,
    action: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 500,
) -> list[AuditEvent]:
    path = audit_path()
    if not path.is_file():
        return []
    events: list[AuditEvent] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev = AuditEvent(
                timestamp=str(raw.get("timestamp", "")),
                actor_user_id=str(raw.get("actor_user_id", "")),
                action=str(raw.get("action", "")),
                entity_type=str(raw.get("entity_type", "")),
                entity_id=str(raw.get("entity_id", "")),
                tenant_id=raw.get("tenant_id"),
                old_value=raw.get("old_value"),
                new_value=raw.get("new_value"),
                detail=str(raw.get("detail") or ""),
                request_id=raw.get("request_id"),
                event_id=str(raw.get("event_id") or uuid.uuid4().hex),
            )
            if tenant_id and ev.tenant_id != tenant_id:
                continue
            if actor_user_id and ev.actor_user_id != actor_user_id:
                continue
            if action and ev.action != action:
                continue
            if date_from and ev.timestamp[:10] < date_from:
                continue
            if date_to and ev.timestamp[:10] > date_to:
                continue
            events.append(ev)
    events.reverse()  # newest first
    return events[: max(1, min(limit, 5000))]

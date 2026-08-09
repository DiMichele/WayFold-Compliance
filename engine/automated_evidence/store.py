from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .domain import (
    AutomatedEvidenceRecord,
    CheckControlMapping,
    ConnectorConfig,
    ConnectorKind,
    EvidenceReviewStatus,
    FindingStatus,
)

from engine.runtime_paths import data_root


def _default_root() -> Path:
    return data_root() / "automated_evidence"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _to_plain(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, list):
        return [_to_plain(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if hasattr(obj, "__dataclass_fields__"):
        return _to_plain(asdict(obj))
    return obj


class AutomatedEvidenceStore:
    """JSON store for connectors + automated evidence (outside CISO DB)."""

    def __init__(self, root: Path | None = None):
        self.root = root or _default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self._connectors = self.root / "connectors.json"
        self._evidence = self.root / "evidence.json"
        self._mappings = self.root / "check_mappings.json"
        for p, default in (
            (self._connectors, {"connectors": []}),
            (self._evidence, {"records": []}),
            (self._mappings, {"mappings": []}),
        ):
            if not p.is_file():
                p.write_text(json.dumps(default, indent=2), encoding="utf-8")

    def now(self) -> str:
        return _now()

    def new_id(self, prefix: str) -> str:
        return _new_id(prefix)

    # --- connectors ---
    def upsert_connector(self, connector: ConnectorConfig) -> ConnectorConfig:
        data = self._load(self._connectors)
        items = data["connectors"]
        plain = _to_plain(connector)
        # Never persist secrets even if mistakenly passed
        plain.pop("credential", None)
        plain.pop("secret", None)
        plain.pop("password", None)
        plain.pop("api_key", None)
        for i, row in enumerate(items):
            if row["id"] == connector.id:
                items[i] = plain
                break
        else:
            items.append(plain)
        self._save(self._connectors, data)
        return connector

    def get_connector(self, connector_id: str) -> ConnectorConfig | None:
        for c in self.list_connectors():
            if c.id == connector_id:
                return c
        return None

    def list_connectors(self, *, tenant_id: str | None = None) -> list[ConnectorConfig]:
        items = [
            self._connector_from_dict(c)
            for c in self._load(self._connectors)["connectors"]
        ]
        if tenant_id:
            items = [c for c in items if c.tenant_id == tenant_id]
        return items

    # --- evidence ---
    def upsert_evidence(self, record: AutomatedEvidenceRecord) -> AutomatedEvidenceRecord:
        data = self._load(self._evidence)
        items = data["records"]
        plain = _to_plain(record)
        for i, row in enumerate(items):
            if row["id"] == record.id:
                items[i] = plain
                break
        else:
            items.append(plain)
        self._save(self._evidence, data)
        return record

    def find_by_dedupe_key(
        self, *, connector_id: str, check_id: str, resource_uid: str, content_hash: str
    ) -> AutomatedEvidenceRecord | None:
        for r in self.list_evidence():
            if (
                r.connector_id == connector_id
                and r.check_id == check_id
                and r.resource_uid == resource_uid
                and r.content_hash == content_hash
            ):
                return r
        return None

    def find_active(
        self, *, connector_id: str, check_id: str, resource_uid: str
    ) -> AutomatedEvidenceRecord | None:
        matches = [
            r
            for r in self.list_evidence()
            if r.connector_id == connector_id
            and r.check_id == check_id
            and r.resource_uid == resource_uid
            and r.review_status != EvidenceReviewStatus.REJECTED
        ]
        matches.sort(key=lambda r: r.last_checked_at or r.created_at, reverse=True)
        return matches[0] if matches else None

    def get_evidence(self, evidence_id: str) -> AutomatedEvidenceRecord | None:
        for r in self.list_evidence():
            if r.id == evidence_id:
                return r
        return None

    def list_evidence(
        self,
        *,
        tenant_id: str | None = None,
        connector_id: str | None = None,
        status: EvidenceReviewStatus | None = None,
    ) -> list[AutomatedEvidenceRecord]:
        items = [
            self._evidence_from_dict(r) for r in self._load(self._evidence)["records"]
        ]
        if tenant_id:
            items = [r for r in items if r.tenant_id == tenant_id]
        if connector_id:
            items = [r for r in items if r.connector_id == connector_id]
        if status:
            items = [r for r in items if r.review_status == status]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items

    # --- extra mappings ---
    def list_extra_mappings(self) -> list[CheckControlMapping]:
        return [
            CheckControlMapping(
                check_id=m["check_id"],
                canonical_control_ref=m["canonical_control_ref"],
                relation=m.get("relation", "SUPPORTING"),
                notes=m.get("notes", ""),
            )
            for m in self._load(self._mappings)["mappings"]
        ]

    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _connector_from_dict(self, d: dict) -> ConnectorConfig:
        return ConnectorConfig(
            id=d["id"],
            tenant_id=d["tenant_id"],
            name=d["name"],
            kind=ConnectorKind(d.get("kind", "PROWLER_JSON")),
            enabled=bool(d.get("enabled", True)),
            source_uri=d.get("source_uri", ""),
            credential_ref=d.get("credential_ref"),
            provider=d.get("provider", "aws"),
            last_checked_at=d.get("last_checked_at"),
            last_ingest_status=d.get("last_ingest_status"),
            notes=d.get("notes", ""),
        )

    def _evidence_from_dict(self, d: dict) -> AutomatedEvidenceRecord:
        return AutomatedEvidenceRecord(
            id=d["id"],
            tenant_id=d["tenant_id"],
            program_id=d.get("program_id"),
            connector_id=d["connector_id"],
            check_id=d["check_id"],
            content_hash=d.get("content_hash", ""),
            canonical_control_ref=d.get("canonical_control_ref", ""),
            implementation_id=d.get("implementation_id"),
            finding_status=FindingStatus(d.get("finding_status", "MANUAL")),
            title=d.get("title", ""),
            description=d.get("description", ""),
            evidence_type=d.get("evidence_type", "EXTERNAL_REFERENCE"),
            external_url=d.get("external_url", ""),
            storage_reference=d.get("storage_reference", ""),
            provider=d.get("provider", ""),
            resource_uid=d.get("resource_uid", ""),
            collected_at=d.get("collected_at", ""),
            last_checked_at=d.get("last_checked_at", ""),
            review_status=EvidenceReviewStatus(d.get("review_status", "PENDING_REVIEW")),
            requires_manual_review=bool(d.get("requires_manual_review", True)),
            provenance=dict(d.get("provenance") or {}),
            created_at=d.get("created_at", ""),
            reviewed_at=d.get("reviewed_at"),
            review_notes=d.get("review_notes", ""),
        )

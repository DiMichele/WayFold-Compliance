from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .domain import (
    ChangeStatus,
    FrameworkUpdateSuggestion,
    RegulatoryChange,
    Source,
    SourceSnapshot,
    SourceType,
    SuggestionStatus,
)

from engine.runtime_paths import data_root


def _default_root() -> Path:
    return data_root() / "regulatory"


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


class RegulatoryStore:
    """JSON-backed engine store — separate from CISO DB."""

    def __init__(self, root: Path | None = None):
        self.root = root or _default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "blobs").mkdir(exist_ok=True)
        self._sources_path = self.root / "sources.json"
        self._snapshots_path = self.root / "snapshots.json"
        self._changes_path = self.root / "changes.json"
        self._suggestions_path = self.root / "framework_suggestions.json"
        for p, default in (
            (self._sources_path, {"sources": []}),
            (self._snapshots_path, {"snapshots": []}),
            (self._changes_path, {"changes": []}),
            (self._suggestions_path, {"suggestions": []}),
        ):
            if not p.is_file():
                p.write_text(json.dumps(default, indent=2), encoding="utf-8")

    # --- sources ---
    def list_sources(self) -> list[Source]:
        return [self._source_from_dict(s) for s in self._load(self._sources_path)["sources"]]

    def get_source(self, source_id: str) -> Source | None:
        for s in self.list_sources():
            if s.id == source_id:
                return s
        return None

    def upsert_source(self, source: Source) -> Source:
        data = self._load(self._sources_path)
        items = data["sources"]
        plain = _to_plain(source)
        for i, existing in enumerate(items):
            if existing["id"] == source.id:
                items[i] = plain
                break
        else:
            items.append(plain)
        self._save(self._sources_path, data)
        return source

    def create_source(self, **kwargs) -> Source:
        sid = kwargs.pop("id", None) or _new_id("src")
        stype = kwargs.get("type", SourceType.HTML)
        if isinstance(stype, str):
            stype = SourceType(stype)
        source = Source(id=sid, type=stype, **{k: v for k, v in kwargs.items() if k != "type"})
        return self.upsert_source(source)

    # --- snapshots / blobs ---
    def write_blob(self, content: str | bytes, *, suffix: str = "txt") -> str:
        if isinstance(content, str):
            raw = content.encode("utf-8")
        else:
            raw = content
        name = f"{_new_id('blob')}.{suffix}"
        path = self.root / "blobs" / name
        path.write_bytes(raw)
        return f"blobs/{name}"

    def read_blob(self, ref: str) -> str:
        path = self.root / ref
        return path.read_text(encoding="utf-8", errors="replace")

    def list_snapshots(self, source_id: str | None = None) -> list[SourceSnapshot]:
        snaps = [
            self._snap_from_dict(s) for s in self._load(self._snapshots_path)["snapshots"]
        ]
        if source_id:
            snaps = [s for s in snaps if s.source_id == source_id]
        snaps.sort(key=lambda s: s.fetched_at)
        return snaps

    def get_snapshot(self, snapshot_id: str) -> SourceSnapshot | None:
        for s in self.list_snapshots():
            if s.id == snapshot_id:
                return s
        return None

    def latest_snapshot(self, source_id: str) -> SourceSnapshot | None:
        snaps = self.list_snapshots(source_id)
        return snaps[-1] if snaps else None

    def add_snapshot(self, snap: SourceSnapshot) -> SourceSnapshot:
        data = self._load(self._snapshots_path)
        data["snapshots"].append(_to_plain(snap))
        self._save(self._snapshots_path, data)
        return snap

    # --- changes ---
    def list_changes(self, *, status: ChangeStatus | None = None) -> list[RegulatoryChange]:
        changes = [
            self._change_from_dict(c) for c in self._load(self._changes_path)["changes"]
        ]
        if status:
            changes = [c for c in changes if c.status == status]
        changes.sort(key=lambda c: c.detected_at, reverse=True)
        return changes

    def get_change(self, change_id: str) -> RegulatoryChange | None:
        for c in self.list_changes():
            if c.id == change_id:
                return c
        return None

    def upsert_change(self, change: RegulatoryChange) -> RegulatoryChange:
        data = self._load(self._changes_path)
        items = data["changes"]
        plain = _to_plain(change)
        for i, existing in enumerate(items):
            if existing["id"] == change.id:
                items[i] = plain
                break
        else:
            items.append(plain)
        self._save(self._changes_path, data)
        return change

    def add_change(self, change: RegulatoryChange) -> RegulatoryChange:
        return self.upsert_change(change)

    # --- suggestions ---
    def list_suggestions(self) -> list[FrameworkUpdateSuggestion]:
        return [
            self._sug_from_dict(s)
            for s in self._load(self._suggestions_path)["suggestions"]
        ]

    def add_suggestion(self, sug: FrameworkUpdateSuggestion) -> FrameworkUpdateSuggestion:
        data = self._load(self._suggestions_path)
        data["suggestions"].append(_to_plain(sug))
        self._save(self._suggestions_path, data)
        return sug

    def upsert_suggestion(self, sug: FrameworkUpdateSuggestion) -> FrameworkUpdateSuggestion:
        data = self._load(self._suggestions_path)
        items = data["suggestions"]
        plain = _to_plain(sug)
        for i, existing in enumerate(items):
            if existing["id"] == sug.id:
                items[i] = plain
                break
        else:
            items.append(plain)
        self._save(self._suggestions_path, data)
        return sug

    def now(self) -> str:
        return _now()

    def new_id(self, prefix: str) -> str:
        return _new_id(prefix)

    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _source_from_dict(self, d: dict) -> Source:
        return Source(
            id=d["id"],
            title=d["title"],
            url=d["url"],
            publisher=d.get("publisher", ""),
            type=SourceType(d.get("type", "HTML")),
            language=d.get("language", "it"),
            official=bool(d.get("official", True)),
            monitoring_enabled=bool(d.get("monitoring_enabled", True)),
            check_frequency_hours=int(d.get("check_frequency_hours", 24)),
            last_checked=d.get("last_checked"),
            last_successful_fetch=d.get("last_successful_fetch"),
            last_content_hash=d.get("last_content_hash"),
            notes=d.get("notes", ""),
            linked_framework_ids=list(d.get("linked_framework_ids") or []),
            linked_requirement_ids=list(d.get("linked_requirement_ids") or []),
            linked_framework_versions=list(d.get("linked_framework_versions") or []),
        )

    def _snap_from_dict(self, d: dict) -> SourceSnapshot:
        return SourceSnapshot(
            id=d["id"],
            source_id=d["source_id"],
            fetched_at=d["fetched_at"],
            content_hash=d["content_hash"],
            normalized_hash=d["normalized_hash"],
            raw_ref=d["raw_ref"],
            normalized_ref=d["normalized_ref"],
            previous_snapshot_id=d.get("previous_snapshot_id"),
            fetch_metadata=dict(d.get("fetch_metadata") or {}),
        )

    def _change_from_dict(self, d: dict) -> RegulatoryChange:
        return RegulatoryChange(
            id=d["id"],
            source_id=d["source_id"],
            old_snapshot_id=d.get("old_snapshot_id"),
            new_snapshot_id=d["new_snapshot_id"],
            detected_at=d["detected_at"],
            raw_diff=d.get("raw_diff", ""),
            summary=d.get("summary", ""),
            relevance=d.get("relevance", "UNKNOWN"),
            status=ChangeStatus(d.get("status", "NEW")),
            potentially_impacted_requirement_ids=list(
                d.get("potentially_impacted_requirement_ids") or []
            ),
            potentially_impacted_control_refs=list(
                d.get("potentially_impacted_control_refs") or []
            ),
            notes=d.get("notes", ""),
        )

    def _sug_from_dict(self, d: dict) -> FrameworkUpdateSuggestion:
        return FrameworkUpdateSuggestion(
            id=d["id"],
            change_id=d["change_id"],
            source_id=d["source_id"],
            framework_ids=list(d.get("framework_ids") or []),
            framework_versions=list(d.get("framework_versions") or []),
            suggested_action=d.get("suggested_action", "REVIEW_MAPPINGS"),
            rationale=d.get("rationale", ""),
            status=SuggestionStatus(d.get("status", "DRAFT")),
            created_at=d.get("created_at", ""),
        )

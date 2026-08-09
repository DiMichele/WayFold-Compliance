from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from .domain import (
    AISuggestion,
    SuggestionKind,
    SuggestionReviewStatus,
    TenantAISettings,
)

from engine.runtime_paths import data_root


def _default_root() -> Path:
    return data_root() / "ai"


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


class AIStore:
    """JSON store for AI suggestions + tenant AI settings (outside CISO DB)."""

    def __init__(self, root: Path | None = None):
        self.root = root or _default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self._suggestions_path = self.root / "suggestions.json"
        self._settings_path = self.root / "tenant_settings.json"
        for p, default in (
            (self._suggestions_path, {"suggestions": []}),
            (self._settings_path, {"tenants": []}),
        ):
            if not p.is_file():
                p.write_text(json.dumps(default, indent=2), encoding="utf-8")

    def now(self) -> str:
        return _now()

    def new_id(self, prefix: str) -> str:
        return _new_id(prefix)

    def get_tenant_settings(self, tenant_id: str) -> TenantAISettings:
        data = self._load(self._settings_path)
        for row in data["tenants"]:
            if row["tenant_id"] == tenant_id:
                return TenantAISettings(
                    tenant_id=tenant_id,
                    ai_processing_enabled=bool(row.get("ai_processing_enabled", False)),
                )
        # Default false — product useful without AI
        return TenantAISettings(tenant_id=tenant_id, ai_processing_enabled=False)

    def set_tenant_ai_processing(self, tenant_id: str, enabled: bool) -> TenantAISettings:
        data = self._load(self._settings_path)
        items = data["tenants"]
        for i, row in enumerate(items):
            if row["tenant_id"] == tenant_id:
                items[i] = {
                    "tenant_id": tenant_id,
                    "ai_processing_enabled": bool(enabled),
                }
                break
        else:
            items.append(
                {"tenant_id": tenant_id, "ai_processing_enabled": bool(enabled)}
            )
        self._save(self._settings_path, data)
        return self.get_tenant_settings(tenant_id)

    def add_suggestion(self, suggestion: AISuggestion) -> AISuggestion:
        data = self._load(self._suggestions_path)
        data["suggestions"].append(_to_plain(suggestion))
        self._save(self._suggestions_path, data)
        return suggestion

    def upsert_suggestion(self, suggestion: AISuggestion) -> AISuggestion:
        data = self._load(self._suggestions_path)
        items = data["suggestions"]
        plain = _to_plain(suggestion)
        for i, existing in enumerate(items):
            if existing["id"] == suggestion.id:
                items[i] = plain
                break
        else:
            items.append(plain)
        self._save(self._suggestions_path, data)
        return suggestion

    def get_suggestion(self, suggestion_id: str) -> AISuggestion | None:
        for s in self.list_suggestions():
            if s.id == suggestion_id:
                return s
        return None

    def list_suggestions(
        self,
        *,
        tenant_id: str | None = None,
        kind: SuggestionKind | None = None,
        status: SuggestionReviewStatus | None = None,
    ) -> list[AISuggestion]:
        items = [
            self._from_dict(s) for s in self._load(self._suggestions_path)["suggestions"]
        ]
        if tenant_id:
            items = [s for s in items if s.tenant_id == tenant_id]
        if kind:
            items = [s for s in items if s.kind == kind]
        if status:
            items = [s for s in items if s.review_status == status]
        items.sort(key=lambda s: s.created_at, reverse=True)
        return items

    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _from_dict(self, d: dict) -> AISuggestion:
        return AISuggestion(
            id=d["id"],
            kind=SuggestionKind(d["kind"]),
            tenant_id=d["tenant_id"],
            program_id=d.get("program_id"),
            subject_ref=d.get("subject_ref", ""),
            review_status=SuggestionReviewStatus(d.get("review_status", "AI_SUGGESTED")),
            provider_name=d.get("provider_name", ""),
            confidence=float(d.get("confidence") or 0),
            summary=d.get("summary", ""),
            payload=dict(d.get("payload") or {}),
            created_at=d.get("created_at", ""),
            reviewed_at=d.get("reviewed_at"),
            review_notes=d.get("review_notes", ""),
        )

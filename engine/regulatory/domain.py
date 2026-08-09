from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SourceType(str, Enum):
    HTML = "HTML"
    PDF = "PDF"
    JSON = "JSON"
    RSS = "RSS"
    API = "API"
    FILE = "FILE"


class ChangeStatus(str, Enum):
    NEW = "NEW"
    ANALYZED = "ANALYZED"
    IGNORED = "IGNORED"
    ACCEPTED = "ACCEPTED"


class SuggestionStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_FOR_HUMAN = "READY_FOR_HUMAN"
    DISMISSED = "DISMISSED"
    APPLIED_MANUALLY = "APPLIED_MANUALLY"


@dataclass
class Source:
    id: str
    title: str
    url: str
    publisher: str = ""
    type: SourceType = SourceType.HTML
    language: str = "it"
    official: bool = True
    monitoring_enabled: bool = True
    check_frequency_hours: int = 24
    last_checked: str | None = None
    last_successful_fetch: str | None = None
    last_content_hash: str | None = None
    notes: str = ""
    # Deterministic impact anchors (no AI): frameworks / requirements in WayFold overlay
    linked_framework_ids: list[str] = field(default_factory=list)
    linked_requirement_ids: list[str] = field(default_factory=list)
    linked_framework_versions: list[str] = field(default_factory=list)


@dataclass
class SourceSnapshot:
    id: str
    source_id: str
    fetched_at: str
    content_hash: str
    normalized_hash: str
    raw_ref: str
    normalized_ref: str
    previous_snapshot_id: str | None = None
    fetch_metadata: dict = field(default_factory=dict)


@dataclass
class RegulatoryChange:
    id: str
    source_id: str
    old_snapshot_id: str | None
    new_snapshot_id: str
    detected_at: str
    raw_diff: str
    summary: str
    relevance: str  # SUBSTANTIVE | COSMETIC | UNKNOWN
    status: ChangeStatus = ChangeStatus.NEW
    potentially_impacted_requirement_ids: list[str] = field(default_factory=list)
    potentially_impacted_control_refs: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class FrameworkUpdateSuggestion:
    """Human-reviewed workflow artifact — never auto-publishes into CISO."""

    id: str
    change_id: str
    source_id: str
    framework_ids: list[str]
    framework_versions: list[str]
    suggested_action: str  # CLONE_DRAFT | REVIEW_MAPPINGS | NO_ACTION
    rationale: str
    status: SuggestionStatus = SuggestionStatus.DRAFT
    created_at: str = ""


@dataclass
class ClientImpactRow:
    tenant_id: str
    tenant_name: str
    program_id: str
    program_name: str
    framework_id: str
    framework_name: str
    framework_version: str
    requirement_ids: list[str]
    control_refs: list[str]


@dataclass
class ClientImpactReport:
    change_id: str
    source_id: str
    requirements: int
    controls: int
    clients: int
    programs: int
    rows: list[ClientImpactRow] = field(default_factory=list)

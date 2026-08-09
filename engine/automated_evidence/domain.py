from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ConnectorKind(str, Enum):
    PROWLER_JSON = "PROWLER_JSON"
    FIXTURE = "FIXTURE"


class FindingStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MANUAL = "MANUAL"
    INFO = "INFO"
    ERROR = "ERROR"


class EvidenceReviewStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class IngestStatus(str, Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED_IDEMPOTENT = "SKIPPED_IDEMPOTENT"


@dataclass
class ConnectorConfig:
    """Scanner connector — secrets only via credential_ref (env name), never inline."""

    id: str
    tenant_id: str
    name: str
    kind: ConnectorKind
    enabled: bool = True
    # Path or URI to fixture/output; never embeds cloud credentials
    source_uri: str = ""
    # Name of environment variable holding credentials if a live scan is configured
    credential_ref: str | None = None
    provider: str = "aws"  # aws|azure|gcp|m365|k8s|generic
    last_checked_at: str | None = None
    last_ingest_status: str | None = None
    notes: str = ""


@dataclass
class NormalizedFinding:
    """Provider-agnostic technical check result."""

    check_id: str
    check_title: str
    status: FindingStatus
    severity: str
    resource_uid: str
    resource_name: str
    provider: str
    region: str = ""
    description: str = ""
    remediation: str = ""
    raw_ref: str = ""
    observed_at: str = ""
    content_hash: str = ""


@dataclass
class CheckControlMapping:
    """Technical check → canonical control (SUPPORTING by default)."""

    check_id: str
    canonical_control_ref: str
    relation: str = "SUPPORTING"  # never implies FULL organizational compliance
    notes: str = ""


@dataclass
class AutomatedEvidenceRecord:
    """Technical evidence suggestion/record — does not auto-close compliance."""

    id: str
    tenant_id: str
    program_id: str | None
    connector_id: str
    check_id: str
    content_hash: str
    canonical_control_ref: str
    implementation_id: str | None
    finding_status: FindingStatus
    title: str
    description: str
    evidence_type: str = "EXTERNAL_REFERENCE"  # aligns with WayFold Evidence types
    external_url: str = ""
    storage_reference: str = ""
    provider: str = ""
    resource_uid: str = ""
    collected_at: str = ""
    last_checked_at: str = ""
    review_status: EvidenceReviewStatus = EvidenceReviewStatus.PENDING_REVIEW
    requires_manual_review: bool = True
    provenance: dict = field(default_factory=dict)
    created_at: str = ""
    reviewed_at: str | None = None
    review_notes: str = ""


@dataclass
class IngestResult:
    connector_id: str
    status: IngestStatus
    findings_total: int = 0
    created: int = 0
    updated: int = 0
    skipped_duplicate: int = 0
    unmapped: int = 0
    errors: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)

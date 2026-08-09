from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CoverageRelation(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    SUPPORTING = "SUPPORTING"


class ImplementationStatus(str, Enum):
    IMPLEMENTED = "IMPLEMENTED"
    IN_PROGRESS = "IN_PROGRESS"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RequirementCoverage(str, Enum):
    FULLY_COVERED = "FULLY_COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    NOT_COVERED = "NOT_COVERED"
    UNMAPPED = "UNMAPPED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    AI_SUGGESTED = "AI_SUGGESTED"
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class MappingRecord:
    """Requirement ↔ CanonicalControl mapping (WayFold overlay on CISO refs)."""

    requirement_id: str
    framework_id: str
    framework_name: str
    framework_version: str
    requirement_code: str
    canonical_control_id: str
    canonical_control_ref: str
    relation: CoverageRelation
    rationale: str = ""
    uncovered_delta: str = ""
    notes: str = ""
    confidence: float | None = None
    review_status: ReviewStatus = ReviewStatus.APPROVED


@dataclass(frozen=True)
class RequirementSnapshot:
    id: str
    framework_id: str
    framework_name: str
    framework_version: str
    code: str
    title: str
    assessable: bool = True
    is_leaf: bool = True
    result: str | None = None  # CISO RequirementAssessment.result


@dataclass(frozen=True)
class ControlImplementationSnapshot:
    id: str
    ref_id: str
    name: str
    canonical_control_id: str | None
    canonical_control_ref: str | None
    status: ImplementationStatus
    owner: str | None = None
    due_date: str | None = None
    priority: str | None = None
    evidence_count: int = 0
    open_task_count: int = 0
    folder_id: str | None = None
    description: str = ""
    not_applicable_rationale: str = ""
    not_applicable_approved_by: str | None = None
    not_applicable_approved_at: str | None = None


@dataclass(frozen=True)
class EvidenceSnapshot:
    """Named evidence artifact attached to one or more controls (demo/catalog)."""

    id: str
    title: str
    filename: str
    control_refs: list[str] = field(default_factory=list)
    status: str = "VALID"  # VALID | REVIEW_REQUIRED | PARTIAL | EXPIRING
    valid_until: str | None = None
    review_by: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class RemediationTaskSnapshot:
    """Remediation / task row for consultant UX (demo overlay)."""

    id: str
    title: str
    control_ref: str | None
    owner: str | None = None
    status: str = "TODO"  # TODO | IN_PROGRESS | REVIEW | DONE
    due_date: str | None = None
    priority: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class ProgramSnapshot:
    """Pinned client program baseline (Folder + Perimeter + assessments)."""

    tenant_id: str
    tenant_name: str
    program_id: str
    program_name: str
    requirements: list[RequirementSnapshot]
    implementations: list[ControlImplementationSnapshot]
    mappings: list[MappingRecord]
    # requirement_id -> implementation ids already linked in core assessments
    requirement_implementation_links: dict[str, list[str]] = field(default_factory=dict)
    scope: str = ""
    program_status: str = "ACTIVE"
    dataset_marker: str = ""
    evidences: list[EvidenceSnapshot] = field(default_factory=list)
    tasks: list[RemediationTaskSnapshot] = field(default_factory=list)
    available_framework_versions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FrameworkCoverageRow:
    framework_id: str
    framework_name: str
    framework_version: str
    requirement_id: str
    requirement_code: str
    relation: CoverageRelation
    uncovered_delta: str
    rationale: str


@dataclass
class ChecklistControlRow:
    control_key: str
    canonical_control_id: str | None
    canonical_control_ref: str | None
    implementation_id: str | None
    name: str
    status: ImplementationStatus
    owner: str | None
    due_date: str | None
    priority: str | None
    evidence_count: int
    open_task_count: int
    framework_coverage: list[FrameworkCoverageRow]
    gap_notes: str = ""


@dataclass
class UnmappedRequirementRow:
    requirement_id: str
    framework_id: str
    framework_name: str
    framework_version: str
    code: str
    title: str
    result: str | None = None


@dataclass
class UnifiedChecklist:
    tenant_id: str
    program_id: str
    program_name: str
    raw_requirement_count: int
    unified_control_count: int
    unmapped: list[UnmappedRequirementRow]
    controls: list[ChecklistControlRow]
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class FrameworkReadinessRow:
    framework_id: str
    framework_name: str
    framework_version: str
    fully_covered: int
    partially_covered: int
    not_covered: int
    unmapped: int
    not_applicable: int
    applicable_total: int
    implemented_applicable: int
    implementation_readiness: float | None
    requirement_breakdown: dict[str, RequirementCoverage]


@dataclass
class ControlImpactRow:
    control_key: str
    canonical_control_ref: str | None
    name: str
    status: ImplementationStatus
    frameworks_impacted: int
    requirements_impacted: int
    open_gap_requirements: int
    readable_summary: str

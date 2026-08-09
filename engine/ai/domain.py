from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SuggestionKind(str, Enum):
    MAPPING = "MAPPING"
    REGULATORY_DIFF = "REGULATORY_DIFF"
    IMPACT = "IMPACT"
    GAP_EXPLANATION = "GAP_EXPLANATION"


class SuggestionReviewStatus(str, Enum):
    AI_SUGGESTED = "AI_SUGGESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class TenantAISettings:
    tenant_id: str
    ai_processing_enabled: bool = False


@dataclass
class AISuggestion:
    """Persisted AI output — never auto-applied to compliance state."""

    id: str
    kind: SuggestionKind
    tenant_id: str
    program_id: str | None
    subject_ref: str  # requirement_id / change_id / control_ref
    review_status: SuggestionReviewStatus = SuggestionReviewStatus.AI_SUGGESTED
    provider_name: str = ""
    confidence: float = 0.0
    summary: str = ""
    payload: dict = field(default_factory=dict)
    created_at: str = ""
    reviewed_at: str | None = None
    review_notes: str = ""


@dataclass
class MappingSuggestionPayload:
    requirement_id: str
    requirement_code: str
    suggested_control_ref: str
    suggested_control_name: str
    relation: str  # FULL|PARTIAL|SUPPORTING
    rationale: str
    uncovered_delta: str
    confidence: float


@dataclass
class RegulatoryDiffSuggestionPayload:
    change_id: str
    is_relevant: bool
    summary: str
    potentially_impacted_requirement_ids: list[str]
    suggested_actions: list[str]
    confidence: float


@dataclass
class ImpactSuggestionPayload:
    change_id: str
    clients: int
    controls: int
    requirements: int
    narrative: str
    recommended_reviews: list[str]
    confidence: float


@dataclass
class GapExplanationPayload:
    requirement_id: str
    requirement_code: str
    coverage: str
    missing_elements: list[str]
    explanation: str
    suggested_remediation: list[str]
    confidence: float

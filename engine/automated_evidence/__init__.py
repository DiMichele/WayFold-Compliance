"""Phase 6 — Automated Evidence (Prowler/fixture adapter → SUPPORTING evidence)."""

from .domain import (
    AutomatedEvidenceRecord,
    ConnectorConfig,
    EvidenceReviewStatus,
    FindingStatus,
)
from .service import AutomatedEvidenceService
from .store import AutomatedEvidenceStore

__all__ = [
    "AutomatedEvidenceRecord",
    "AutomatedEvidenceService",
    "AutomatedEvidenceStore",
    "ConnectorConfig",
    "EvidenceReviewStatus",
    "FindingStatus",
]

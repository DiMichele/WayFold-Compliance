"""WayFold Regulatory Intelligence (Phase 4) — deterministic, no AI.

Pipeline: fetch → normalize → hash → compare → diff → RegulatoryChange → impact.
Does not mutate CISO published libraries or client baselines.
"""

from .domain import (
    ChangeStatus,
    ClientImpactReport,
    FrameworkUpdateSuggestion,
    RegulatoryChange,
    Source,
    SourceSnapshot,
    SourceType,
)
from .pipeline import check_source, review_change, run_monitoring_pass
from .store import RegulatoryStore

__all__ = [
    "ChangeStatus",
    "ClientImpactReport",
    "FrameworkUpdateSuggestion",
    "RegulatoryChange",
    "RegulatoryStore",
    "Source",
    "SourceSnapshot",
    "SourceType",
    "check_source",
    "review_change",
    "run_monitoring_pass",
]

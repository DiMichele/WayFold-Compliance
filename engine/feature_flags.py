"""Server-side feature flags. Hidden UI is not sufficient — routes must deny."""

from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def ai_enabled() -> bool:
    return _flag("WAYFOLD_FEATURE_AI", False)


def framework_suggestions_enabled() -> bool:
    return _flag("WAYFOLD_FEATURE_FW_SUGGESTIONS", False)


def connectors_enabled() -> bool:
    return _flag("WAYFOLD_FEATURE_CONNECTORS", False)


def automated_evidence_enabled() -> bool:
    return _flag("WAYFOLD_FEATURE_AUTO_EVIDENCE", False)


def is_feature_path(path: str) -> str | None:
    """Return feature name if path belongs to a gated feature, else None."""
    p = path.rstrip("/") or "/"
    if p.startswith(("/ai", "/api/ai")):
        return "ai"
    if p.startswith(("/fw-suggestions", "/api/fw-suggestions", "/framework-suggestions")):
        return "fw_suggestions"
    if p.startswith(("/connectors", "/api/auto-evidence/connectors")):
        return "connectors"
    if p.startswith(("/auto-evidence", "/api/auto-evidence")):
        return "auto_evidence"
    return None


def feature_allowed(feature: str) -> bool:
    return {
        "ai": ai_enabled,
        "fw_suggestions": framework_suggestions_enabled,
        "connectors": connectors_enabled,
        "auto_evidence": automated_evidence_enabled,
    }.get(feature, lambda: True)()

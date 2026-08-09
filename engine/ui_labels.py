"""Centralized status / mapping / priority labels for WayFold Compliance UI.

Backend enums stay in English; the UI always renders via these helpers.
"""

from __future__ import annotations

from typing import Any

from engine.i18n import normalize_lang, t

# Canonical backend → message key
STATUS_LABEL_KEYS: dict[str, str] = {
    "IMPLEMENTED": "status.implemented",
    "IN_PROGRESS": "status.in_progress",
    "NOT_IMPLEMENTED": "status.not_implemented",
    "NOT_APPLICABLE": "status.not_applicable",
    "UNMAPPED": "status.unmapped",
    "TODO": "task.todo",
    "REVIEW": "task.review",
    "DONE": "task.done",
    "VALID": "evidence.valid",
    "REVIEW_REQUIRED": "evidence.needs_review",
    "NEEDS_REVIEW": "evidence.needs_review",
    "PARTIAL": "evidence.partial",
    "EXPIRING": "evidence.expiring",
    "EXPIRED": "evidence.expired",
}

MAPPING_LABEL_KEYS: dict[str, str] = {
    "FULL": "mapping.full",
    "PARTIAL": "mapping.partial",
    "SUPPORTING": "mapping.supporting",
    "UNMAPPED": "mapping.unmapped",
}

PRIORITY_LABEL_KEYS: dict[str, str] = {
    "HIGH": "priority.high",
    "MEDIUM": "priority.medium",
    "LOW": "priority.low",
    "CRITICAL": "priority.critical",
}

REVIEW_LABEL_KEYS: dict[str, str] = {
    "DRAFT": "review.draft",
    "APPROVED": "review.approved",
    "REJECTED": "review.rejected",
    "HUMAN_REVIEWED": "review.human_reviewed",
    "NEEDS_REVIEW": "review.needs_review",
    "PENDING": "review.pending",
    "ACCEPTED": "review.accepted",
    "IGNORED": "review.ignored",
    "DISMISSED": "reg.dismissed",
    "NEW": "reg.new",
    "REVIEW": "reg.review",
    "ANALYZED": "reg.analyzed",
}

RELEVANCE_LABEL_KEYS: dict[str, str] = {
    "NEW": "reg.new",
    "SUBSTANTIVE": "reg.substantive",
    "COSMETIC": "review.ignored",
    "ANALYZED": "reg.analyzed",
}

FRAMEWORK_STATUS_KEYS: dict[str, str] = {
    "DRAFT": "fw.draft",
    "PUBLISHED": "fw.published",
    "RETIRED": "fw.retired",
    "DEPRECATED": "fw.deprecated",
    "ARCHIVED": "fw.archived",
    "ACTIVE": "status.active",
}

EVIDENCE_STATUS_KEYS: dict[str, str] = {
    "VALID": "evidence.valid",
    "NEEDS_REVIEW": "evidence.needs_review",
    "REVIEW_REQUIRED": "evidence.needs_review",
    "PARTIAL": "evidence.partial",
    "EXPIRING": "evidence.expiring",
    "EXPIRED": "evidence.expired",
    "MISSING": "evidence.missing",
    "OK": "evidence.ok",
}

# Badge visual variants
STATUS_VARIANTS: dict[str, str] = {
    "IMPLEMENTED": "success",
    "IN_PROGRESS": "warning",
    "NOT_IMPLEMENTED": "danger",
    "NOT_APPLICABLE": "neutral",
    "UNMAPPED": "violet",
    "TODO": "neutral",
    "REVIEW": "warning",
    "DONE": "success",
    "VALID": "success",
    "REVIEW_REQUIRED": "warning",
    "NEEDS_REVIEW": "warning",
    "PARTIAL": "warning",
    "EXPIRING": "warning",
    "EXPIRED": "danger",
}

MAPPING_VARIANTS: dict[str, str] = {
    "FULL": "success",
    "PARTIAL": "warning",
    "SUPPORTING": "violet",
    "UNMAPPED": "danger",
}

PRIORITY_VARIANTS: dict[str, str] = {
    "CRITICAL": "danger",
    "HIGH": "danger",
    "MEDIUM": "warning",
    "LOW": "info",
}

REVIEW_VARIANTS: dict[str, str] = {
    "DRAFT": "violet",
    "APPROVED": "success",
    "REJECTED": "danger",
    "HUMAN_REVIEWED": "success",
    "NEEDS_REVIEW": "warning",
    "PENDING": "warning",
    "ACCEPTED": "success",
    "IGNORED": "neutral",
}


def _norm(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip().upper().replace(" ", "_")


def status_label(lang: str, value: Any) -> str:
    key = STATUS_LABEL_KEYS.get(_norm(value))
    return t(lang, key) if key else (str(value) if value else "—")


def mapping_label(lang: str, value: Any) -> str:
    key = MAPPING_LABEL_KEYS.get(_norm(value))
    return t(lang, key) if key else (str(value) if value else "—")


def priority_label(lang: str, value: Any) -> str:
    if value is None or value == "":
        return "—"
    key = PRIORITY_LABEL_KEYS.get(_norm(value))
    return t(lang, key) if key else str(value)


def review_label(lang: str, value: Any) -> str:
    key = REVIEW_LABEL_KEYS.get(_norm(value))
    return t(lang, key) if key else (str(value) if value else "—")


def relevance_label(lang: str, value: Any) -> str:
    key = RELEVANCE_LABEL_KEYS.get(_norm(value))
    return t(lang, key) if key else (str(value) if value else "—")


def framework_status_label(lang: str, value: Any) -> str:
    key = FRAMEWORK_STATUS_KEYS.get(_norm(value))
    return t(lang, key) if key else (str(value) if value else "—")


def evidence_status_label(lang: str, value: Any) -> str:
    key = EVIDENCE_STATUS_KEYS.get(_norm(value))
    return t(lang, key) if key else (str(value) if value else "—")


def status_variant(value: Any) -> str:
    return STATUS_VARIANTS.get(_norm(value), "neutral")


def mapping_variant(value: Any) -> str:
    return MAPPING_VARIANTS.get(_norm(value), "neutral")


def priority_variant(value: Any) -> str:
    return PRIORITY_VARIANTS.get(_norm(value), "neutral")


def review_variant(value: Any) -> str:
    return REVIEW_VARIANTS.get(_norm(value), "neutral")


def format_percent(value: float | None, *, lang: str = "it") -> str:
    if value is None:
        return "—"
    lang = normalize_lang(lang)
    pct = round(value * 100)
    return f"{pct}%" if lang == "en" else f"{pct}%"


def format_number(value: int | float, *, lang: str = "it") -> str:
    lang = normalize_lang(lang)
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") if lang == "it" else f"{value:,.1f}"
    n = int(value)
    if lang == "it":
        return f"{n:,}".replace(",", ".")
    return f"{n:,}"

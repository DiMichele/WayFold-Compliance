from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.domain import CoverageRelation, ProgramSnapshot, RequirementSnapshot
from engine.regulatory.domain import ClientImpactReport, RegulatoryChange, Source


@dataclass
class ProviderMappingOut:
    suggested_control_ref: str
    suggested_control_name: str
    relation: str
    rationale: str
    uncovered_delta: str
    confidence: float


@dataclass
class ProviderRegulatoryOut:
    is_relevant: bool
    summary: str
    potentially_impacted_requirement_ids: list[str]
    suggested_actions: list[str]
    confidence: float


@dataclass
class ProviderImpactOut:
    narrative: str
    recommended_reviews: list[str]
    confidence: float


@dataclass
class ProviderGapOut:
    coverage: str
    missing_elements: list[str]
    explanation: str
    suggested_remediation: list[str]
    confidence: float


class AIProvider(Protocol):
    """Abstraction — UI/API must never call an LLM SDK directly."""

    name: str

    def suggest_mapping(
        self, requirement: RequirementSnapshot, program: ProgramSnapshot
    ) -> ProviderMappingOut | None: ...

    def summarize_regulatory_diff(
        self,
        change: RegulatoryChange,
        source: Source,
        *,
        known_requirement_ids: list[str],
    ) -> ProviderRegulatoryOut: ...

    def suggest_impact(
        self, change: RegulatoryChange, impact: ClientImpactReport
    ) -> ProviderImpactOut: ...

    def explain_gap(
        self,
        requirement: RequirementSnapshot,
        program: ProgramSnapshot,
        *,
        mapping_relation: str | None,
        uncovered_delta: str,
        impl_status: str | None,
        evidence_count: int,
        open_tasks: int,
    ) -> ProviderGapOut: ...


class DisabledAIProvider:
    """Used when tenant.ai_processing_enabled is false."""

    name = "disabled"

    def suggest_mapping(self, requirement, program):  # noqa: ARG002
        return None

    def summarize_regulatory_diff(self, change, source, *, known_requirement_ids):  # noqa: ARG002
        raise RuntimeError("ai_processing_disabled")

    def suggest_impact(self, change, impact):  # noqa: ARG002
        raise RuntimeError("ai_processing_disabled")

    def explain_gap(self, requirement, program, **kwargs):  # noqa: ARG002
        raise RuntimeError("ai_processing_disabled")


class HeuristicAIProvider:
    """Deterministic local assist — no external LLM, no product credentials.

    Produces structured suggestions via keyword/token overlap so overnight
    automation and demos work without API keys. Replaceable by a real LLM
    provider implementing the same AIProvider contract.
    """

    name = "heuristic-v1"

    def suggest_mapping(
        self, requirement: RequirementSnapshot, program: ProgramSnapshot
    ) -> ProviderMappingOut | None:
        tokens = _tokens(f"{requirement.code} {requirement.title}")
        best = None
        best_score = 0.0
        for impl in program.implementations:
            if not impl.canonical_control_ref:
                continue
            score = _jaccard(tokens, _tokens(f"{impl.canonical_control_ref} {impl.name}"))
            # Prefer already-linked controls lightly
            if requirement.id in (
                rid
                for rid, iids in program.requirement_implementation_links.items()
                if impl.id in iids
            ):
                score += 0.15
            if score > best_score:
                best_score = score
                best = impl
        if best is None or best_score < 0.08:
            return None
        relation = CoverageRelation.PARTIAL.value
        uncovered = ""
        if best_score >= 0.45:
            relation = CoverageRelation.FULL.value
        else:
            uncovered = (
                f"Heuristic overlap only ({best_score:.2f}); confirm framework-specific delta"
            )
        return ProviderMappingOut(
            suggested_control_ref=best.canonical_control_ref or best.ref_id,
            suggested_control_name=best.name,
            relation=relation,
            rationale=(
                f"Token overlap between requirement '{requirement.code}' and control "
                f"'{best.canonical_control_ref}' (score={best_score:.2f}). AI_SUGGESTED only."
            ),
            uncovered_delta=uncovered,
            confidence=min(0.85, round(best_score, 3)),
        )

    def summarize_regulatory_diff(
        self,
        change: RegulatoryChange,
        source: Source,
        *,
        known_requirement_ids: list[str],
    ) -> ProviderRegulatoryOut:
        relevant = change.relevance == "SUBSTANTIVE"
        impacted = list(
            dict.fromkeys(
                list(change.potentially_impacted_requirement_ids)
                + list(source.linked_requirement_ids)
                + list(known_requirement_ids)
            )
        )
        actions = []
        if relevant:
            actions = [
                "Human-review RegulatoryChange",
                "If accepted, open FrameworkUpdateSuggestion CLONE_DRAFT",
                "Review client impact before any baseline migration",
            ]
        else:
            actions = ["Ignore cosmetic churn unless policy requires audit trail"]
        summary = (
            f"Source '{source.title}' change relevance={change.relevance}. "
            f"{change.summary[:280]}"
        )
        return ProviderRegulatoryOut(
            is_relevant=relevant,
            summary=summary,
            potentially_impacted_requirement_ids=impacted[:40],
            suggested_actions=actions,
            confidence=0.7 if relevant else 0.55,
        )

    def suggest_impact(
        self, change: RegulatoryChange, impact: ClientImpactReport
    ) -> ProviderImpactOut:
        reviews = [
            f"Review program {r.program_id} ({r.tenant_name}) — frameworks "
            f"{r.framework_name}@{r.framework_version}"
            for r in impact.rows[:12]
        ]
        narrative = (
            f"Potential impact for change {change.id}: {impact.requirements} requirements, "
            f"{impact.controls} controls, {impact.clients} clients, {impact.programs} programs. "
            "Advisory only — does not migrate pinned baselines."
        )
        return ProviderImpactOut(
            narrative=narrative,
            recommended_reviews=reviews,
            confidence=0.65 if impact.rows else 0.4,
        )

    def explain_gap(
        self,
        requirement: RequirementSnapshot,
        program: ProgramSnapshot,  # noqa: ARG002
        *,
        mapping_relation: str | None,
        uncovered_delta: str,
        impl_status: str | None,
        evidence_count: int,
        open_tasks: int,
    ) -> ProviderGapOut:
        coverage = mapping_relation or "UNMAPPED"
        missing: list[str] = []
        if coverage == "UNMAPPED":
            missing.append("No approved mapping to a canonical control")
        if uncovered_delta:
            missing.append(f"Uncovered delta: {uncovered_delta}")
        if impl_status in {None, "NOT_IMPLEMENTED"}:
            missing.append("Control implementation not started")
        elif impl_status == "IN_PROGRESS":
            missing.append("Control implementation still in progress")
        if evidence_count <= 0:
            missing.append("No evidence attached")
        if open_tasks > 0:
            missing.append(f"{open_tasks} open remediation task(s)")
        explanation = (
            f"Requirement {requirement.code} ({requirement.title}) coverage={coverage}, "
            f"implementation={impl_status or 'n/a'}, evidence={evidence_count}. "
            "Explanation is AI_SUGGESTED and does not close the gap."
        )
        remediation = [
            "Confirm or create human-approved mapping",
            "Attach evidence meeting the requirement wording",
            "Close open tasks or set realistic deadline/owner",
        ]
        if coverage == "UNMAPPED":
            remediation.insert(0, "Run mapping suggestion then human-approve before use")
        return ProviderGapOut(
            coverage=coverage,
            missing_elements=missing,
            explanation=explanation,
            suggested_remediation=remediation,
            confidence=0.6,
        )


def _tokens(text: str) -> set[str]:
    raw = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    stop = {
        "the",
        "and",
        "for",
        "with",
        "a",
        "di",
        "del",
        "della",
        "e",
        "la",
        "il",
        "control",
        "access",
    }
    return {t for t in raw.split() if len(t) > 2 and t not in stop}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

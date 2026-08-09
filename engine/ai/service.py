from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from engine.checklist import build_unified_checklist
from engine.domain import CoverageRelation, MappingRecord, ProgramSnapshot, ReviewStatus
from engine.regulatory.pipeline import impact_for_change
from engine.regulatory.store import RegulatoryStore

from .domain import (
    AISuggestion,
    GapExplanationPayload,
    ImpactSuggestionPayload,
    MappingSuggestionPayload,
    RegulatoryDiffSuggestionPayload,
    SuggestionKind,
    SuggestionReviewStatus,
    TenantAISettings,
)
from .provider import AIProvider, DisabledAIProvider, HeuristicAIProvider
from .store import AIStore


class AIProcessingDisabled(RuntimeError):
    pass


class AIAssistanceService:
    """AI suggests; humans approve. Never auto-closes compliance."""

    def __init__(
        self,
        store: AIStore | None = None,
        *,
        provider: AIProvider | None = None,
        regulatory_store: RegulatoryStore | None = None,
    ):
        self.store = store or AIStore()
        self._default_provider = provider or HeuristicAIProvider()
        self.regulatory_store = regulatory_store or RegulatoryStore()

    def tenant_settings(self, tenant_id: str) -> TenantAISettings:
        return self.store.get_tenant_settings(tenant_id)

    def set_ai_processing(self, tenant_id: str, enabled: bool) -> TenantAISettings:
        return self.store.set_tenant_ai_processing(tenant_id, enabled)

    def _provider_for(self, tenant_id: str) -> AIProvider:
        settings = self.store.get_tenant_settings(tenant_id)
        if not settings.ai_processing_enabled:
            return DisabledAIProvider()
        return self._default_provider

    def suggest_mapping(
        self, program: ProgramSnapshot, requirement_id: str
    ) -> AISuggestion:
        provider = self._provider_for(program.tenant_id)
        if isinstance(provider, DisabledAIProvider):
            raise AIProcessingDisabled(
                f"ai_processing_disabled:{program.tenant_id}"
            )
        req = next((r for r in program.requirements if r.id == requirement_id), None)
        if req is None:
            req = next(
                (r for r in program.requirements if r.code == requirement_id), None
            )
        if req is None:
            raise KeyError(f"requirement_not_found:{requirement_id}")

        out = provider.suggest_mapping(req, program)
        if out is None:
            payload = MappingSuggestionPayload(
                requirement_id=req.id,
                requirement_code=req.code,
                suggested_control_ref="",
                suggested_control_name="",
                relation="SUPPORTING",
                rationale="No suitable control found by provider",
                uncovered_delta="Unmapped — human must choose or leave unmapped",
                confidence=0.0,
            )
            summary = f"No mapping suggestion for {req.code}"
            confidence = 0.0
        else:
            payload = MappingSuggestionPayload(
                requirement_id=req.id,
                requirement_code=req.code,
                suggested_control_ref=out.suggested_control_ref,
                suggested_control_name=out.suggested_control_name,
                relation=out.relation,
                rationale=out.rationale,
                uncovered_delta=out.uncovered_delta,
                confidence=out.confidence,
            )
            summary = (
                f"Suggest {out.suggested_control_ref} ({out.relation}) for {req.code}"
            )
            confidence = out.confidence

        return self._persist(
            kind=SuggestionKind.MAPPING,
            tenant_id=program.tenant_id,
            program_id=program.program_id,
            subject_ref=req.id,
            provider_name=provider.name,
            confidence=confidence,
            summary=summary,
            payload=asdict(payload),
        )

    def summarize_regulatory_change(
        self,
        change_id: str,
        *,
        tenant_id: str,
        program: ProgramSnapshot | None = None,
    ) -> AISuggestion:
        provider = self._provider_for(tenant_id)
        if isinstance(provider, DisabledAIProvider):
            raise AIProcessingDisabled(f"ai_processing_disabled:{tenant_id}")
        change = self.regulatory_store.get_change(change_id)
        if change is None:
            raise KeyError(f"change_not_found:{change_id}")
        source = self.regulatory_store.get_source(change.source_id)
        if source is None:
            raise KeyError(f"source_not_found:{change.source_id}")
        # Never feed another tenant's program requirements into the suggestion payload
        if program is not None and program.tenant_id != tenant_id:
            program = None
        known = [r.id for r in program.requirements] if program else []
        out = provider.summarize_regulatory_diff(
            change, source, known_requirement_ids=known
        )
        payload = RegulatoryDiffSuggestionPayload(
            change_id=change.id,
            is_relevant=out.is_relevant,
            summary=out.summary,
            potentially_impacted_requirement_ids=out.potentially_impacted_requirement_ids,
            suggested_actions=out.suggested_actions,
            confidence=out.confidence,
        )
        return self._persist(
            kind=SuggestionKind.REGULATORY_DIFF,
            tenant_id=tenant_id,
            program_id=program.program_id if program else None,
            subject_ref=change.id,
            provider_name=provider.name,
            confidence=out.confidence,
            summary=out.summary[:400],
            payload=asdict(payload),
        )

    def suggest_impact(
        self,
        change_id: str,
        *,
        tenant_id: str,
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
    ) -> AISuggestion:
        provider = self._provider_for(tenant_id)
        if isinstance(provider, DisabledAIProvider):
            raise AIProcessingDisabled(f"ai_processing_disabled:{tenant_id}")
        change = self.regulatory_store.get_change(change_id)
        if change is None:
            raise KeyError(f"change_not_found:{change_id}")
        impact = impact_for_change(
            change_id,
            self.regulatory_store,
            actor_tenant_ids=actor_tenant_ids or {tenant_id},
            is_superuser=is_superuser,
        )
        out = provider.suggest_impact(change, impact)
        payload = ImpactSuggestionPayload(
            change_id=change_id,
            clients=impact.clients,
            controls=impact.controls,
            requirements=impact.requirements,
            narrative=out.narrative,
            recommended_reviews=out.recommended_reviews,
            confidence=out.confidence,
        )
        return self._persist(
            kind=SuggestionKind.IMPACT,
            tenant_id=tenant_id,
            program_id=None,
            subject_ref=change_id,
            provider_name=provider.name,
            confidence=out.confidence,
            summary=out.narrative[:400],
            payload=asdict(payload),
        )

    def explain_gap(
        self, program: ProgramSnapshot, requirement_id: str
    ) -> AISuggestion:
        provider = self._provider_for(program.tenant_id)
        if isinstance(provider, DisabledAIProvider):
            raise AIProcessingDisabled(
                f"ai_processing_disabled:{program.tenant_id}"
            )
        req = next((r for r in program.requirements if r.id == requirement_id), None)
        if req is None:
            req = next(
                (r for r in program.requirements if r.code == requirement_id), None
            )
        if req is None:
            raise KeyError(f"requirement_not_found:{requirement_id}")

        checklist = build_unified_checklist(program)
        mapping_relation = None
        uncovered = ""
        impl_status = None
        evidence = 0
        tasks = 0
        for u in checklist.unmapped:
            if u.requirement_id == req.id:
                mapping_relation = "UNMAPPED"
        for ctrl in checklist.controls:
            for cov in ctrl.framework_coverage:
                if cov.requirement_id == req.id:
                    mapping_relation = cov.relation.value
                    uncovered = cov.uncovered_delta or ""
                    impl_status = ctrl.status.value
                    evidence = ctrl.evidence_count
                    tasks = ctrl.open_task_count
        if mapping_relation is None:
            mapping_relation = "UNMAPPED"

        out = provider.explain_gap(
            req,
            program,
            mapping_relation=mapping_relation,
            uncovered_delta=uncovered,
            impl_status=impl_status,
            evidence_count=evidence,
            open_tasks=tasks,
        )
        payload = GapExplanationPayload(
            requirement_id=req.id,
            requirement_code=req.code,
            coverage=out.coverage,
            missing_elements=out.missing_elements,
            explanation=out.explanation,
            suggested_remediation=out.suggested_remediation,
            confidence=out.confidence,
        )
        return self._persist(
            kind=SuggestionKind.GAP_EXPLANATION,
            tenant_id=program.tenant_id,
            program_id=program.program_id,
            subject_ref=req.id,
            provider_name=provider.name,
            confidence=out.confidence,
            summary=out.explanation[:400],
            payload=asdict(payload),
        )

    def review_suggestion(
        self,
        suggestion_id: str,
        *,
        status: SuggestionReviewStatus,
        notes: str = "",
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
    ) -> AISuggestion:
        if status not in {
            SuggestionReviewStatus.APPROVED,
            SuggestionReviewStatus.REJECTED,
        }:
            raise ValueError("review_status_must_be_APPROVED_or_REJECTED")
        sug = self.store.get_suggestion(suggestion_id)
        if sug is None:
            raise KeyError(f"suggestion_not_found:{suggestion_id}")
        if not is_superuser:
            allowed = set(actor_tenant_ids or ())
            if sug.tenant_id not in allowed:
                raise PermissionError("tenant_isolation_denied")
        if sug.review_status != SuggestionReviewStatus.AI_SUGGESTED:
            raise ValueError(f"already_reviewed:{sug.review_status.value}")
        sug.review_status = status
        sug.reviewed_at = self.store.now()
        sug.review_notes = notes
        return self.store.upsert_suggestion(sug)

    def materialize_approved_mapping(
        self, suggestion_id: str, program: ProgramSnapshot
    ) -> MappingRecord:
        """Build a MappingRecord from an APPROVED suggestion — does not persist into CISO.

        Caller may overlay/store externally. Never marks client compliant.
        """
        sug = self.store.get_suggestion(suggestion_id)
        if sug is None:
            raise KeyError(f"suggestion_not_found:{suggestion_id}")
        if sug.kind != SuggestionKind.MAPPING:
            raise ValueError("not_a_mapping_suggestion")
        if sug.review_status != SuggestionReviewStatus.APPROVED:
            raise ValueError("mapping_not_human_approved")
        if sug.tenant_id != program.tenant_id:
            raise PermissionError("tenant_isolation_denied")
        p = sug.payload
        ctrl_ref = p.get("suggested_control_ref") or ""
        if not ctrl_ref:
            raise ValueError("empty_suggested_control")
        impl = next(
            (
                i
                for i in program.implementations
                if i.canonical_control_ref == ctrl_ref or i.ref_id == ctrl_ref
            ),
            None,
        )
        req = next(
            (r for r in program.requirements if r.id == p.get("requirement_id")), None
        )
        if req is None:
            raise KeyError("requirement_missing_on_program")
        return MappingRecord(
            requirement_id=req.id,
            framework_id=req.framework_id,
            framework_name=req.framework_name,
            framework_version=req.framework_version,
            requirement_code=req.code,
            canonical_control_id=impl.canonical_control_id if impl else ctrl_ref,
            canonical_control_ref=ctrl_ref,
            relation=CoverageRelation(p.get("relation") or "PARTIAL"),
            rationale=p.get("rationale") or "",
            uncovered_delta=p.get("uncovered_delta") or "",
            notes="Materialized from human-approved AI suggestion; not auto-applied to baseline",
            confidence=float(p.get("confidence") or sug.confidence or 0),
            review_status=ReviewStatus.APPROVED,
        )

    def list_suggestions(
        self,
        *,
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
        tenant_id: str | None = None,
        kind: SuggestionKind | None = None,
        status: SuggestionReviewStatus | None = None,
    ) -> list[AISuggestion]:
        items = self.store.list_suggestions(tenant_id=tenant_id, kind=kind, status=status)
        if is_superuser:
            return items
        allowed = set(actor_tenant_ids or ())
        return [s for s in items if s.tenant_id in allowed]

    def _persist(
        self,
        *,
        kind: SuggestionKind,
        tenant_id: str,
        program_id: str | None,
        subject_ref: str,
        provider_name: str,
        confidence: float,
        summary: str,
        payload: dict,
    ) -> AISuggestion:
        sug = AISuggestion(
            id=self.store.new_id("ais"),
            kind=kind,
            tenant_id=tenant_id,
            program_id=program_id,
            subject_ref=subject_ref,
            review_status=SuggestionReviewStatus.AI_SUGGESTED,
            provider_name=provider_name,
            confidence=confidence,
            summary=summary,
            payload=payload,
            created_at=self.store.now(),
        )
        return self.store.add_suggestion(sug)


def default_ai_service(root: Path | None = None) -> AIAssistanceService:
    return AIAssistanceService(store=AIStore(root))

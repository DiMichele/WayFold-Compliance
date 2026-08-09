from __future__ import annotations

from pathlib import Path

from engine.domain import ProgramSnapshot

from .adapters import load_adapter
from .domain import (
    AutomatedEvidenceRecord,
    ConnectorConfig,
    ConnectorKind,
    EvidenceReviewStatus,
    FindingStatus,
    IngestResult,
    IngestStatus,
)
from .mapping import resolve_control_refs
from .store import AutomatedEvidenceStore


class AutomatedEvidenceService:
    """Ingest technical scanner output → evidence suggestions. Never auto-closes compliance."""

    def __init__(self, store: AutomatedEvidenceStore | None = None):
        self.store = store or AutomatedEvidenceStore()

    def upsert_connector(self, connector: ConnectorConfig) -> ConnectorConfig:
        if connector.credential_ref and (
            " " in connector.credential_ref or connector.credential_ref.startswith("sk-")
        ):
            # Reject obvious inline secrets; credential_ref must be an env var name
            raise ValueError("credential_ref_must_be_env_var_name")
        return self.store.upsert_connector(connector)

    def list_connectors(
        self,
        *,
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
        tenant_id: str | None = None,
    ) -> list[ConnectorConfig]:
        items = self.store.list_connectors(tenant_id=tenant_id)
        if is_superuser:
            return items
        allowed = set(actor_tenant_ids or ())
        return [c for c in items if c.tenant_id in allowed]

    def ingest_connector(
        self,
        connector_id: str,
        *,
        program: ProgramSnapshot | None = None,
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
        payload: bytes | str | Path | None = None,
    ) -> IngestResult:
        connector = self.store.get_connector(connector_id)
        if connector is None:
            raise KeyError(f"connector_not_found:{connector_id}")
        if not is_superuser:
            allowed = set(actor_tenant_ids or ())
            if connector.tenant_id not in allowed:
                raise PermissionError("tenant_isolation_denied")
        if program is not None and program.tenant_id != connector.tenant_id:
            raise PermissionError("tenant_isolation_denied")
        if not connector.enabled:
            return IngestResult(
                connector_id=connector_id,
                status=IngestStatus.FAILED,
                errors=["connector_disabled"],
            )

        try:
            adapter = load_adapter(connector.kind.value)
            source = payload if payload is not None else self._resolve_source(connector)
            findings = adapter.parse(source, observed_at=self.store.now())
        except Exception as exc:  # noqa: BLE001 — isolate scanner failure
            connector.last_checked_at = self.store.now()
            connector.last_ingest_status = IngestStatus.FAILED.value
            self.store.upsert_connector(connector)
            return IngestResult(
                connector_id=connector_id,
                status=IngestStatus.FAILED,
                errors=[f"scanner_failure:{type(exc).__name__}:{exc}"],
            )

        result = IngestResult(
            connector_id=connector_id,
            status=IngestStatus.OK,
            findings_total=len(findings),
        )
        extra_maps = self.store.list_extra_mappings()
        now = self.store.now()

        for finding in findings:
            maps = resolve_control_refs(finding.check_id, extra_maps)
            if not maps:
                result.unmapped += 1
                continue
            for mapping in maps:
                impl_id = None
                if program is not None:
                    impl = next(
                        (
                            i
                            for i in program.implementations
                            if i.canonical_control_ref == mapping.canonical_control_ref
                            or i.ref_id == mapping.canonical_control_ref
                        ),
                        None,
                    )
                    impl_id = impl.id if impl else None

                existing_same = self.store.find_by_dedupe_key(
                    connector_id=connector.id,
                    check_id=finding.check_id,
                    resource_uid=finding.resource_uid,
                    content_hash=finding.content_hash,
                )
                if existing_same is not None:
                    # Idempotent re-ingest: refresh last_checked only
                    existing_same.last_checked_at = now
                    self.store.upsert_evidence(existing_same)
                    result.skipped_duplicate += 1
                    result.evidence_ids.append(existing_same.id)
                    continue

                prior = self.store.find_active(
                    connector_id=connector.id,
                    check_id=finding.check_id,
                    resource_uid=finding.resource_uid,
                )
                if prior is not None and prior.content_hash != finding.content_hash:
                    prior.review_status = EvidenceReviewStatus.STALE
                    prior.last_checked_at = now
                    self.store.upsert_evidence(prior)

                # Even PASS requires human review — technical signal ≠ organizational compliance
                record = AutomatedEvidenceRecord(
                    id=self.store.new_id("aev"),
                    tenant_id=connector.tenant_id,
                    program_id=program.program_id if program else None,
                    connector_id=connector.id,
                    check_id=finding.check_id,
                    content_hash=finding.content_hash,
                    canonical_control_ref=mapping.canonical_control_ref,
                    implementation_id=impl_id,
                    finding_status=finding.status,
                    title=f"[auto] {finding.check_title}",
                    description=(
                        f"{finding.description}\n"
                        f"Relation={mapping.relation}. "
                        f"Technical {finding.status.value} is SUPPORTING evidence only — "
                        f"does not mark the control/requirement compliant."
                    ).strip(),
                    evidence_type="EXTERNAL_REFERENCE",
                    external_url="",
                    storage_reference=finding.raw_ref,
                    provider=finding.provider or connector.provider,
                    resource_uid=finding.resource_uid,
                    collected_at=finding.observed_at or now,
                    last_checked_at=now,
                    review_status=EvidenceReviewStatus.PENDING_REVIEW,
                    requires_manual_review=True,
                    provenance={
                        "adapter": adapter.name,
                        "connector_id": connector.id,
                        "check_id": finding.check_id,
                        "severity": finding.severity,
                        "region": finding.region,
                        "mapping_relation": mapping.relation,
                        "mapping_notes": mapping.notes,
                        "remediation": finding.remediation,
                    },
                    created_at=now,
                )
                self.store.upsert_evidence(record)
                if prior is None:
                    result.created += 1
                else:
                    result.updated += 1
                result.evidence_ids.append(record.id)

        if result.errors:
            result.status = IngestStatus.PARTIAL
        elif result.created == 0 and result.updated == 0 and result.skipped_duplicate > 0:
            result.status = IngestStatus.SKIPPED_IDEMPOTENT

        connector.last_checked_at = now
        connector.last_ingest_status = result.status.value
        self.store.upsert_connector(connector)
        return result

    def review_evidence(
        self,
        evidence_id: str,
        *,
        status: EvidenceReviewStatus,
        notes: str = "",
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
    ) -> AutomatedEvidenceRecord:
        if status not in {
            EvidenceReviewStatus.APPROVED,
            EvidenceReviewStatus.REJECTED,
        }:
            raise ValueError("review_status_must_be_APPROVED_or_REJECTED")
        rec = self.store.get_evidence(evidence_id)
        if rec is None:
            raise KeyError(f"evidence_not_found:{evidence_id}")
        if not is_superuser:
            allowed = set(actor_tenant_ids or ())
            if rec.tenant_id not in allowed:
                raise PermissionError("tenant_isolation_denied")
        if rec.review_status not in {
            EvidenceReviewStatus.PENDING_REVIEW,
            EvidenceReviewStatus.STALE,
        }:
            raise ValueError(f"already_reviewed:{rec.review_status.value}")
        rec.review_status = status
        rec.reviewed_at = self.store.now()
        rec.review_notes = notes
        return self.store.upsert_evidence(rec)

    def list_evidence(
        self,
        *,
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
        tenant_id: str | None = None,
        status: EvidenceReviewStatus | None = None,
    ) -> list[AutomatedEvidenceRecord]:
        items = self.store.list_evidence(tenant_id=tenant_id, status=status)
        if is_superuser:
            return items
        allowed = set(actor_tenant_ids or ())
        return [r for r in items if r.tenant_id in allowed]

    def approved_evidence_for_control(
        self,
        *,
        tenant_id: str,
        canonical_control_ref: str,
        actor_tenant_ids: set[str] | None = None,
        is_superuser: bool = False,
    ) -> list[AutomatedEvidenceRecord]:
        if not is_superuser:
            allowed = set(actor_tenant_ids or ())
            if tenant_id not in allowed:
                raise PermissionError("tenant_isolation_denied")
        return [
            r
            for r in self.store.list_evidence(tenant_id=tenant_id)
            if r.canonical_control_ref == canonical_control_ref
            and r.review_status == EvidenceReviewStatus.APPROVED
        ]

    def project_evidence_counts(
        self, program: ProgramSnapshot
    ) -> dict[str, int]:
        """Advisory counts of APPROVED automated evidence per control ref.

        Does not mutate program implementations or CISO AppliedControl status.
        """
        counts: dict[str, int] = {}
        for r in self.store.list_evidence(tenant_id=program.tenant_id):
            if r.review_status != EvidenceReviewStatus.APPROVED:
                continue
            if program.program_id and r.program_id and r.program_id != program.program_id:
                continue
            counts[r.canonical_control_ref] = counts.get(r.canonical_control_ref, 0) + 1
        return counts

    def _resolve_source(self, connector: ConnectorConfig) -> Path:
        uri = connector.source_uri
        if uri.startswith("fixture://"):
            rel = uri.removeprefix("fixture://")
            base = Path(__file__).resolve().parents[1] / "fixtures" / "automated_evidence"
            path = base / rel
        else:
            path = Path(uri)
        if not path.is_file():
            raise FileNotFoundError(f"source_not_found:{uri}")
        return path


def default_auto_evidence_service(root: Path | None = None) -> AutomatedEvidenceService:
    return AutomatedEvidenceService(store=AutomatedEvidenceStore(root))

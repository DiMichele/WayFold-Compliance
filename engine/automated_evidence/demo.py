from __future__ import annotations

from pathlib import Path

from engine.domain import ProgramSnapshot
from engine.program_loader import load_program_snapshot

from .domain import ConnectorConfig, ConnectorKind
from .service import AutomatedEvidenceService
from .store import AutomatedEvidenceStore

FIXTURE_REL = "prowler-aws-sample.json"
DEFAULT_PROGRAM = (
    Path(__file__).resolve().parents[1] / "fixtures" / "michele_phase2_program.json"
)


def seed_demo_connector(
    store: AutomatedEvidenceStore | None = None,
    *,
    tenant_id: str = "tenant-michele",
) -> ConnectorConfig:
    svc = AutomatedEvidenceService(store or AutomatedEvidenceStore())
    connector = ConnectorConfig(
        id="conn-prowler-michele-demo",
        tenant_id=tenant_id,
        name="Prowler AWS (fixture demo)",
        kind=ConnectorKind.PROWLER_JSON,
        enabled=True,
        source_uri=f"fixture://{FIXTURE_REL}",
        credential_ref=None,  # fixture path — no cloud credentials
        provider="aws",
        notes=(
            "Demo connector using Prowler-compatible JSON fixture. "
            "Live Prowler scan deferred (Windows path ENVIRONMENT BLOCKER)."
        ),
    )
    return svc.upsert_connector(connector)


def run_demo_ingest(
    store: AutomatedEvidenceStore | None = None,
    *,
    program: ProgramSnapshot | None = None,
) -> dict:
    store = store or AutomatedEvidenceStore()
    svc = AutomatedEvidenceService(store)
    connector = seed_demo_connector(store)
    program = program or load_program_snapshot(DEFAULT_PROGRAM)
    first = svc.ingest_connector(
        connector.id, program=program, is_superuser=True
    )
    second = svc.ingest_connector(
        connector.id, program=program, is_superuser=True
    )
    return {
        "connector_id": connector.id,
        "first": first,
        "second": second,
        "evidence": svc.list_evidence(is_superuser=True, tenant_id=connector.tenant_id),
    }

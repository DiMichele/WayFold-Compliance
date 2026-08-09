"""Seed a controllable local demo source (no external network)."""

from __future__ import annotations

from pathlib import Path

from .domain import Source, SourceType
from .pipeline import DEFAULT_FIXTURE_ROOT, check_source
from .store import RegulatoryStore

DEMO_SOURCE_ID = "src-demo-nis2"


def seed_demo_source(store: RegulatoryStore, *, url: str | None = None) -> Source:
    source = Source(
        id=DEMO_SOURCE_ID,
        title="Demo NIS2 privileged access notice",
        url=url or "fixture://demo-nis2/v1.html",
        publisher="WayFold Demo",
        type=SourceType.HTML,
        language="it",
        official=True,
        monitoring_enabled=True,
        check_frequency_hours=1,
        notes="Local fixture source for Phase 4 deterministic demo",
        linked_framework_ids=["fw-b"],
        linked_framework_versions=["2026.1"],
        linked_requirement_ids=["req-b-01", "NIS2-IAM"],
    )
    return store.upsert_source(source)


def run_demo_change_cycle(
    store: RegulatoryStore,
    *,
    fixture_root: Path | None = None,
) -> dict:
    """Baseline v1 → substantive v2 → review ACCEPTED + impact."""
    fixture_root = fixture_root or DEFAULT_FIXTURE_ROOT
    source = seed_demo_source(store, url="fixture://demo-nis2/v1.html")
    baseline = check_source(source, store, fixture_root=fixture_root)

    source.url = "fixture://demo-nis2/v2.html"
    store.upsert_source(source)
    changed = check_source(source, store, fixture_root=fixture_root)

    return {
        "baseline": baseline,
        "changed": changed,
        "source_id": source.id,
    }

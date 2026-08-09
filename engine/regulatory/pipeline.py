from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .diff import classify_relevance, summarize_diff, unified_diff
from .domain import (
    ChangeStatus,
    FrameworkUpdateSuggestion,
    RegulatoryChange,
    Source,
    SourceSnapshot,
    SuggestionStatus,
)
from .fetch import fetch_url
from .hashutil import content_hash
from .impact import project_client_impact, resolve_controls_for_requirements
from .normalize import normalize_content
from .store import RegulatoryStore

DEFAULT_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "regulatory"


@dataclass
class CheckResult:
    source_id: str
    ok: bool
    changed: bool
    snapshot_id: str | None = None
    change_id: str | None = None
    relevance: str | None = None
    error: str | None = None
    message: str = ""


def check_source(
    source: Source,
    store: RegulatoryStore,
    *,
    fixture_root: Path | None = None,
    create_cosmetic_change: bool = False,
) -> CheckResult:
    """fetch → normalize → hash → compare → optional RegulatoryChange.

    Never mutates CISO libraries or client programs.
    """
    fixture_root = fixture_root or DEFAULT_FIXTURE_ROOT
    fetched_at = store.now()
    source.last_checked = fetched_at
    store.upsert_source(source)

    result = fetch_url(source.url, fixture_root=fixture_root)
    if not result.ok:
        store.upsert_source(source)
        return CheckResult(
            source_id=source.id,
            ok=False,
            changed=False,
            error=result.error,
            message=f"fetch_failed:{result.error}",
        )

    try:
        text = result.content.decode("utf-8")
    except UnicodeDecodeError:
        text = result.content.decode("utf-8", errors="replace")

    # Adapter hint from source type
    ctype = result.content_type
    if source.type.value == "JSON":
        ctype = "application/json"
    elif source.type.value in {"HTML", "FILE"}:
        if "html" not in ctype and source.url.endswith((".html", ".htm")):
            ctype = "text/html"

    normalized = normalize_content(text, content_type=ctype)
    raw_hash = content_hash(text)
    norm_hash = content_hash(normalized)

    previous = store.latest_snapshot(source.id)
    raw_ref = store.write_blob(text, suffix=_suffix_for(ctype))
    norm_ref = store.write_blob(normalized, suffix="txt")

    snap = SourceSnapshot(
        id=store.new_id("snap"),
        source_id=source.id,
        fetched_at=fetched_at,
        content_hash=raw_hash,
        normalized_hash=norm_hash,
        raw_ref=raw_ref,
        normalized_ref=norm_ref,
        previous_snapshot_id=previous.id if previous else None,
        fetch_metadata={
            **(result.metadata or {}),
            "content_type": ctype,
            "bytes": len(result.content),
        },
    )
    store.add_snapshot(snap)
    source.last_successful_fetch = fetched_at
    source.last_content_hash = raw_hash
    store.upsert_source(source)

    if previous is None:
        return CheckResult(
            source_id=source.id,
            ok=True,
            changed=False,
            snapshot_id=snap.id,
            message="baseline_snapshot_created",
        )

    raw_changed = previous.content_hash != raw_hash
    norm_changed = previous.normalized_hash != norm_hash
    relevance = classify_relevance(raw_changed=raw_changed, normalized_changed=norm_changed)

    if relevance == "NONE":
        return CheckResult(
            source_id=source.id,
            ok=True,
            changed=False,
            snapshot_id=snap.id,
            relevance=relevance,
            message="no_change",
        )

    if relevance == "COSMETIC" and not create_cosmetic_change:
        return CheckResult(
            source_id=source.id,
            ok=True,
            changed=False,
            snapshot_id=snap.id,
            relevance=relevance,
            message="cosmetic_change_ignored",
        )

    old_norm = store.read_blob(previous.normalized_ref)
    new_norm = normalized
    diff_text = unified_diff(old_norm, new_norm, fromfile=previous.id, tofile=snap.id)
    summary = summarize_diff(diff_text)

    req_ids = list(source.linked_requirement_ids)
    ctrl_refs = resolve_controls_for_requirements(req_ids)

    change = RegulatoryChange(
        id=store.new_id("chg"),
        source_id=source.id,
        old_snapshot_id=previous.id,
        new_snapshot_id=snap.id,
        detected_at=fetched_at,
        raw_diff=diff_text[:20000],
        summary=summary,
        relevance=relevance,
        status=ChangeStatus.NEW,
        potentially_impacted_requirement_ids=req_ids,
        potentially_impacted_control_refs=ctrl_refs,
    )
    store.add_change(change)

    return CheckResult(
        source_id=source.id,
        ok=True,
        changed=True,
        snapshot_id=snap.id,
        change_id=change.id,
        relevance=relevance,
        message="regulatory_change_created",
    )


def run_monitoring_pass(
    store: RegulatoryStore,
    *,
    fixture_root: Path | None = None,
) -> list[CheckResult]:
    """Check all monitoring-enabled sources; one failure does not stop others."""
    results: list[CheckResult] = []
    for source in store.list_sources():
        if not source.monitoring_enabled:
            continue
        try:
            results.append(check_source(source, store, fixture_root=fixture_root))
        except Exception as exc:  # noqa: BLE001
            results.append(
                CheckResult(
                    source_id=source.id,
                    ok=False,
                    changed=False,
                    error=str(exc),
                    message="unhandled_error",
                )
            )
    return results


def review_change(
    change_id: str,
    store: RegulatoryStore,
    *,
    status: ChangeStatus,
    notes: str = "",
    create_framework_suggestion: bool = True,
) -> RegulatoryChange:
    """Human review: ACCEPTED / IGNORED / ANALYZED. No silent framework publish."""
    change = store.get_change(change_id)
    if change is None:
        raise KeyError(f"change_not_found:{change_id}")
    if status not in {
        ChangeStatus.ACCEPTED,
        ChangeStatus.IGNORED,
        ChangeStatus.ANALYZED,
        ChangeStatus.NEW,
    }:
        raise ValueError(f"invalid_status:{status}")
    change.status = status
    if notes:
        change.notes = notes
    store.upsert_change(change)

    if status == ChangeStatus.ACCEPTED and create_framework_suggestion:
        source = store.get_source(change.source_id)
        if source and (source.linked_framework_ids or source.linked_framework_versions):
            sug = FrameworkUpdateSuggestion(
                id=store.new_id("sug"),
                change_id=change.id,
                source_id=source.id,
                framework_ids=list(source.linked_framework_ids),
                framework_versions=list(source.linked_framework_versions),
                suggested_action="CLONE_DRAFT",
                rationale=(
                    "Accepted regulatory change suggests cloning the pinned FrameworkVersion "
                    "into a DRAFT for human edit/publish. Client baselines stay pinned."
                ),
                status=SuggestionStatus.READY_FOR_HUMAN,
                created_at=store.now(),
            )
            store.add_suggestion(sug)
    return change


def impact_for_change(
    change_id: str,
    store: RegulatoryStore,
    *,
    actor_tenant_ids: set[str] | None = None,
    is_superuser: bool = False,
    **kwargs,
):
    change = store.get_change(change_id)
    if change is None:
        raise KeyError(f"change_not_found:{change_id}")
    source = store.get_source(change.source_id)
    if source is None:
        raise KeyError(f"source_not_found:{change.source_id}")
    return project_client_impact(
        change,
        source,
        store=store,
        actor_tenant_ids=actor_tenant_ids,
        is_superuser=is_superuser,
        **kwargs,
    )


def _suffix_for(content_type: str) -> str:
    ct = (content_type or "").lower()
    if "html" in ct:
        return "html"
    if "json" in ct:
        return "json"
    return "txt"

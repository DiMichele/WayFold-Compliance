# PHASE 2 VERIFICATION — WayFold Compliance

## Verdict

**PASS**

## Commit / tree verified

Working tree on branch `automation/wayfold-compliance` (HEAD `92f9eb5` + local authz hardenings applied during this verification run).

Core: **CISO Assistant Community** (Strategy B). Phase 2 capability lives in `apps/wayfold-compliance/engine/` (overlay services; no fork of core domain tables).

## Acceptance matrix

| Criterion | Result | Evidence |
|---|---|---|
| Reuse Canonical / `ReferenceControl` without duplicating core | PASS | `canonical_control_ref` maps to CISO `ReferenceControl` / AppliedControl; no WayFold control table in core DB (`data-model.md`, `ciso_bridge.py`) |
| Mapping FULL / PARTIAL / SUPPORTING + rationale / delta | PASS | `MappingRecord` + Michele fixture; PARTIAL/SUPPORTING keep `uncovered_delta`; readiness never promotes PARTIAL→FULL |
| Unified Checklist **service** (not UI-only) | PASS | `engine/checklist.py` `build_unified_checklist`; CLI + `/api/unified-checklist` consume the same service |
| Unmapped requirements visible | PASS | Fixture codes `A.9.9`, `NIS2-X9`; checklist + HTML section + tests |
| Framework Readiness FULLY / PARTIALLY / NOT_COVERED / UNMAPPED / NOT_APPLICABLE | PASS | `engine/readiness.py`; N/A via assessment `result=not_applicable`; UI column N/A |
| Control Impact / ROI transparent | PASS | `rank_control_impact` readable summaries (no opaque score) |
| Version pinning | PASS | `framework_version` on requirements, mappings, coverage, unmapped rows |
| Tenant isolation + RBAC on new endpoints | PASS | `assert_tenant_access`; API/CLI **default deny** without `--superuser` / `actor_tenants`; cross-tenant → 403 (fixed in this verify) |
| Demo Michele multi-framework | PASS | `michele_phase2_program.json`: 3 FW, shared `CTRL-IAM-001`, PARTIAL+SUPPORTING, ≥2 UNMAPPED, mixed statuses |
| Tests dedup / partial / unmapped | PASS | `python -m engine.tests.test_unified_compliance` → **13 OK** |
| No AI / regulatory watcher in scope | PASS | No watcher/AI packages or endpoints in Phase 2 engine |
| Blocking TODO / FIXME / mock / stub | PASS | None blocking in engine runtime path |

## Tests

| Suite | Result | Notes |
|---|---|---|
| `engine.tests.test_unified_compliance` | PASS | 13 tests incl. HTTP authz, CLI default-deny, NOT_APPLICABLE |
| Live CISO Docker export | Not required for gate | Bridge present; fixture-driven verification sufficient for Phase 2 service |

## Failures / fixes

| Attempt | Issue | Fix |
|---|---|---|
| 1 | API/CLI treated empty `actor_tenants` as superuser (authz bypass) | Default deny (`401 authentication_required`); require explicit `superuser=1` or `actor_tenants`; readiness dedup; N/A column; tests |

`fixAttemptsUsed: 1`

## Warnings (non-blocking)

1. Phase 2 consultant UI remains a dense local HTML surface (`:8092`); full portfolio UX is Phase 3.
2. Mapping overlay persists as JSON / ProgramSnapshot (by design — Strategy B); not a core migration.
3. Optimistic locking integer `version` on AppliedControl still absent upstream (carried from Phase 1).

## Final verdict

**PASS** — Phase 2 Unified Compliance accepted. Orchestrator may tag `phase-2-complete` after its own checks. Do not treat this file as a git tag.

# PHASE 0 RECOMMENDATION — WayFold Compliance

```text
CORE RECOMMENDATION
CISO Assistant

STRATEGY
B — Existing GRC Core + Wayfold Regulatory Engine

WHY
- ~90% domain-model fit on core GRC capabilities (AVAILABLE/PARTIAL weighted; see open-source-evaluation.md)
- ReferenceControl ≈ CanonicalControl
- AppliedControl ≈ Client implementation / ControlImplementation
- Folder(DOMAIN) ≈ Client (ADAPT UX)
- Perimeter ≈ scope/program (ADAPT UX)
- RequirementNode ≈ Requirement
- Evidence already available
- Remediation/tasks already available (TaskNode + AppliedControl ETA/status)
- multi-framework assessment available (demo: ISO27001 + NIS2 + NIST CSF)
- API usable for external extension (DRF/OpenAPI)
- Frameworks are data (YAML libraries), not hardcoded
- Demo Michele acceptance: PASS (reuse of one AppliedControl across 3 frameworks verified)

REUSE
Framework engine (LoadedLibrary / Framework / RequirementNode)
Assessment (ComplianceAssessment / RequirementAssessment)
Reference controls
Applied controls
Evidence
Remediation / tasks
Users / RBAC
Folders (domains)
Perimeters
Library import/export
Docker compose baseline

ADAPT
Unified checklist UX (multi-assessment consultant view)
Portfolio dashboard (multi-client)
Framework version pin/publish UX
Client / program naming & baseline visibility
Mapping review workflow states (DRAFT / HUMAN_REVIEWED / …)

CUSTOM WAYFOLD
Regulatory watcher
Regulatory diff
Client-impact engine
Control ROI
Advanced mapping intelligence

SPECIALIZED COMPONENT
OpenCRE concepts/API for cross-framework relationships
Trestle/OSCAL for structured import/export (later)
Prowler for automated technical evidence (Phase 6)

DO NOT BUILD
Auth
Evidence engine
Task engine
Generic GRC backend
```

## Scorecard summary (decision gate)

| Criterio | Peso | CISO | Probo | Unicis |
|---|---:|---:|---:|---:|
| Domain model fit | 10 | 5 | 4 | 2 |
| Reuse | 9 | 5 | 4 | 3 |
| API/extensibility | 8 | 5 | 5 | 4 |
| Maintainability | 7 | 4 | 4 | 3 |
| Multi-client | 7 | 4 | 4 | 4 |
| Mapping | 7 | 5 | 4 | 4 |
| Evidence/tasks | 6 | 5 | 5 | 3 |
| Deploy | 5 | 4 | 4 | 4 |
| UX | 3 | 3 | 4 | 4 |
| Language preference | 1 | 3 | 3 | 4 |

Secondo classificato: **Probo** (non eseguito in locale: scelta non dubbia dopo scorecard + demo CISO PASS).

## Demo / runtime status

- Stack: Docker Compose prebuilt images (`vendor/ciso-assistant-community`)
- UI: `https://localhost:8443` (HTTP 302)
- API health: `https://localhost:8443/api/health/` → `{"status":"ok"}`
- Admin: `admin@wayfold.local` (password locale solo macchina demo)
- Seed: `docs/michele_demo_seed.py`

## Environment blockers (non decisionali)

- CISO first boot lento (storelibraries) → healthcheck temporarily unhealthy; resolved after wait (**ENVIRONMENT**)
- Prowler Windows path length → partial clone (**ENVIRONMENT**, specialized only)

## Product blockers

- Nessuno di classe 4 sul core selezionato.

## Proposed Phase 1

1. Formalizzare `apps/wayfold-compliance` come wrapper/ops intorno al core CISO (compose override, env, ingress target `compliance.wayfold.xyz`).
2. Script idempotente di bootstrap demo + documentazione comandi in `PROGRESS.md`.
3. Thin consultant UX adaptations: Client/Program naming, portfolio list, unified checklist read-model via CISO API (no new GRC backend).
4. Non iniziare Regulatory Watcher (Phase 4) né AI (Phase 5).

## Stop

Phase -1 + Phase 0 complete. **Do not auto-start Phase 1** without explicit go-ahead.

# Transition 3 → 4 — VERIFY Phase 3, DEVELOP Phase 4

Sessione indipendente. Ricostruisci contesto dal repository.

## PART A — VERIFY PHASE {{VERIFY_PHASE}}

Verifica Consultant UX in modo avversariale:

- Portfolio / Client dashboard utili operativamente
- Gap Assessment
- Owner / Deadline views
- Evidence / Task UX
- Reports
- Workflow consulente
- RBAC / tenant isolation
- regressioni Phase 1–2
- niente Regulatory Watcher prematuro
- build/test/E2E critici

FAIL → FIX → REVERIFY (max {{MAX_FIX_ATTEMPTS}}). Report in `{{VERIFY_REPORT_PATH}}`.

## PART B — DEVELOP PHASE {{DEVELOP_PHASE}} (solo se PASS)

Phase 4 — Regulatory Intelligence (prima logica deterministica, NO AI):

- Sources
- Source adapters / fetchers
- Snapshots + hashes
- Diff
- Regulatory changes
- Framework update workflow
- Client impact

Rispetta confini DB: engine Wayfold separato; niente silent mutation di library pubblicate nel core. API del core solo via canali documentati.

Fine: `PHASE 4 IMPLEMENTATION FINISHED / AWAITING INDEPENDENT VERIFICATION`.

## STOP

JSON → `{{RESULT_PATH}}`.

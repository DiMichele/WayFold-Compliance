# Transition 2 → 3 — VERIFY Phase 2, DEVELOP Phase 3

Sessione nuova. Nessuna memoria del run che ha sviluppato Phase 2. Ricostruisci da repo + master plan + PROGRESS + DECISIONS + architecture/data-model + git log.

## PART A — VERIFY PHASE {{VERIFY_PHASE}}

Reviewer avversariale su Unified Compliance.

Verifica almeno:

- reuse Canonical/ReferenceControl senza duplicare il core
- mapping FULL/PARTIAL/SUPPORTING con rationale/delta
- Unified Checklist service (non solo UI)
- Unmapped Requirements visibili
- Framework Readiness (FULLY/PARTIALLY/NOT_COVERED/UNMAPPED/NOT_APPLICABLE)
- Control Impact/ROI trasparente
- version pinning
- tenant isolation + RBAC sui nuovi endpoint
- demo Michele multi-framework
- test dedup / partial / unmapped
- niente AI / regulatory watcher fuori scope
- TODO/FIXME/mock/stub bloccanti

FAIL → FIX → REVERIFY (max {{MAX_FIX_ATTEMPTS}}). Su FAIL finale non sviluppare Phase 3.

PASS → close docs + `{{VERIFY_REPORT_PATH}}` (Verdict PASS/FAIL binario). No tag manuali.

## PART B — DEVELOP PHASE {{DEVELOP_PHASE}} (solo se PASS)

Phase 3 — Consultant UX (NO Regulatory Watcher):

- Portfolio Dashboard
- Client Dashboard
- Gap Assessment
- Owner view
- Deadline view
- Evidence UX
- Task UX
- Reports
- Consultant workflow quotidiano

Reuse UI patterns del core. Test + docs. Fine:

```text
PHASE 3 IMPLEMENTATION FINISHED
AWAITING INDEPENDENT VERIFICATION
```

## STOP

Scrivi `{{RESULT_PATH}}` e termina.

# Transition 4 → 5 — VERIFY Phase 4, DEVELOP Phase 5

Sessione indipendente.

## PART A — VERIFY PHASE {{VERIFY_PHASE}}

Verifica Regulatory Intelligence:

- Sources + adapters
- Snapshots immutabili con hash
- Diff deterministico
- Regulatory changes tracciati
- Framework update workflow
- Client impact
- nessuna AI decisoria nascosta
- isolation / auth
- migrations additive only (distruttive → BLOCKED/HUMAN)
- regressioni cross-phase

FAIL → FIX → REVERIFY (max {{MAX_FIX_ATTEMPTS}}). `{{VERIFY_REPORT_PATH}}`.

## PART B — DEVELOP PHASE {{DEVELOP_PHASE}} (solo se PASS)

Phase 5 — AI Assistance (suggerisce, non decide):

- AIProvider abstraction
- Mapping suggestions
- Regulatory diff summaries
- Impact suggestions
- Gap explanations
- Human review obbligatoria
- Tenant AI processing setting

AI non chiude compliance autonomamente. Nessuna auto-approvazione mapping/impact.

Fine: `PHASE 5 IMPLEMENTATION FINISHED / AWAITING INDEPENDENT VERIFICATION`.

## STOP

JSON → `{{RESULT_PATH}}`.

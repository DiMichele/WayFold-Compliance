# Transition 5 → 6 — VERIFY Phase 5, DEVELOP Phase 6

Sessione indipendente.

## PART A — VERIFY PHASE {{VERIFY_PHASE}}

Verifica AI safeguards:

- AIProvider abstraction reale
- suggerimenti mapping/diff/impact/gap
- human review gate obbligatorio
- setting tenant per AI processing
- AI non muta stato compliance senza approvazione
- no secrets nei log
- tenant isolation
- regressioni

FAIL → FIX → REVERIFY (max {{MAX_FIX_ATTEMPTS}}). `{{VERIFY_REPORT_PATH}}`.

## PART B — DEVELOP PHASE {{DEVELOP_PHASE}} (solo se PASS)

Phase 6 — Automated Evidence (scope limitato al piano):

- integrazioni evidence automatiche previste
- Prowler o equivalente SOLO se coerente con DECISIONS.md
- cloud providers / external integrations in modo mirato
- non trasformare la fase in un progetto cloud-security infinito
- reuse evidence engine del core

Fine: `PHASE 6 IMPLEMENTATION FINISHED / AWAITING INDEPENDENT VERIFICATION`.

## STOP

JSON → `{{RESULT_PATH}}`.

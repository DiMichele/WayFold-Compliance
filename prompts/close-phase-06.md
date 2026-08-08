# Close Phase 6 — VERIFY ONLY + prepare final regression

Sessione indipendente. **Non sviluppare Phase 7.**

## PART A — VERIFY PHASE {{VERIFY_PHASE}}

Verifica Automated Evidence in modo avversariale:

- integrazioni evidence nello scope del master plan
- Prowler/equivalente coerente con decisioni
- authorization evidence
- tenant isolation
- niente scope creep cloud-security infinito
- regressioni Phase 1–5
- TODO/FIXME/mock bloccanti
- build/test

FAIL → FIX → REVERIFY (max {{MAX_FIX_ATTEMPTS}}).

PASS → close Phase 6 docs + `{{VERIFY_REPORT_PATH}}` con Verdict PASS.

## PART B — NONE

- `developedPhase`: null
- `developmentStatus`: `SKIPPED`
- Aggiorna `{{PROGRESS_PATH}}` e `{{AUTOMATION_REPORT_PATH}}`
- L'orchestratore eseguirà FINAL REGRESSION GATE e merge su main

## STOP

Scrivi JSON in `{{RESULT_PATH}}` con `verificationStatus` finale e termina.

# Transition 1 → 2 — VERIFY Phase 1, DEVELOP Phase 2

Agisci in una sessione **nuova e indipendente**. Non hai memoria del run che ha sviluppato Phase 1.

Ricostruisci tutto da repository:

1. `.cursor/plans/WAYFOLD COMPLIANCE.md`
2. `{{PROGRESS_PATH}}`
3. `{{DECISIONS_PATH}}`
4. `apps/wayfold-compliance/docs/architecture.md`
5. `apps/wayfold-compliance/docs/data-model.md` (se esiste)
6. `git status` / `git log --oneline -30`

---

## PART A — VERIFY PHASE {{VERIFY_PHASE}}

Mindset avversariale: cerca motivi per **NON** dichiarare Phase 1 completa.

### Acceptance criteria (ricostruisci dal piano)

Phase 1 = Working Core. Deve funzionare realmente:

- Client / tenant (Folder/Perimeter CISO o equivalente deciso)
- Framework / requirements caricati come dati
- Controls / ReferenceControl / AppliedControl
- Assessment
- Evidence
- Task / remediation
- Owner / deadline se previsti dal core
- RBAC + tenant isolation server-side
- Demo Michele riproducibile
- Migrations / bootstrap DB pulito
- Test + production build pertinenti
- Docker startup del core selezionato quando applicabile

### Checks obbligatori quando applicabili

feature completeness, domain correctness, unit/integration/E2E critici, build, Docker, migrations, fresh DB, tenant isolation, RBAC, evidence access, optimistic locking se presente, framework version pinning, regressioni, demo Michele, error handling, TODO/FIXME/HACK, mock/stub/placeholder, hardcoded demo logic.

### Fix loop

Se FAIL:

1. FIX i findings bloccanti
2. riesegui i test pertinenti
3. REVERIFY **tutti** gli acceptance criteria pertinenti (non solo la patch)
4. massimo `{{MAX_FIX_ATTEMPTS}}` tentativi automatici

Se dopo i tentativi resta FAIL o BLOCKED: **non** iniziare Phase 2. Scrivi result JSON con `verificationStatus: FAIL|BLOCKED` e `developmentStatus: NOT_STARTED`.

### Close (solo su PASS)

- Scrivi `{{VERIFY_REPORT_PATH}}` con Verdict binario PASS, commit verificato, matrix criteri, test, build, security, demo, failures/fixes, warnings, Final verdict
- Aggiorna `{{PROGRESS_PATH}}` e `{{AUTOMATION_REPORT_PATH}}`
- **Non** creare tag `phase-1-complete` (lo fa l'orchestratore)
- **Non** modificare `{{STATE_PATH}}`

Verdict ammessi: esclusivamente `PASS` o `FAIL` (o `BLOCKED` se ambiente impossibile). Vietato: MOSTLY PASS / GOOD ENOUGH.

---

## PART B — DEVELOP PHASE {{DEVELOP_PHASE}} (solo se PART A = PASS)

Scope Phase 2 — Unified Compliance (NO AI):

- Canonical / common control reuse (riusando ReferenceControl o equivalente del core)
- Cross-framework mapping FULL / PARTIAL / SUPPORTING
- Unified Checklist
- Unmapped Requirements
- Framework Readiness
- Control Impact / ROI leggibile

Principi: REUSE → ADAPT → EXTEND → CUSTOM solo se necessario. Non duplicare auth/tenant/evidence/tasks.

Demo Michele: almeno 3 framework con controllo condiviso, mapping PARTIAL+delta, UNMAPPED, stati misti.

Documentazione: `unified-compliance.md`, PROGRESS, architecture/data-model, ADR solo se necessario.

Al termine:

```text
PHASE 2 IMPLEMENTATION FINISHED
AWAITING INDEPENDENT VERIFICATION
```

Non dire PHASE 2 COMPLETE. Non iniziare Phase 3. Non creare tag.

---

## STOP

Scrivi il JSON in `{{RESULT_PATH}}` e termina questo agent run.

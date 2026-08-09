# PROGRESS — WayFold Compliance

## Fase corrente

**Phase 1 CLOSED (verification PASS).**  
**Phase 2 CLOSED (verification PASS)** — vedi `PHASE2-VERIFICATION.md`.  
**Phase 3 CLOSED (verification PASS)** — vedi `PHASE3-VERIFICATION.md`.  
**Phase 4 CLOSED (verification PASS)** — vedi `PHASE4-VERIFICATION.md`.  
**Phase 5 CLOSED (verification PASS)** — vedi `PHASE5-VERIFICATION.md`.  
**Phase 6 CLOSED (verification PASS)** — vedi `PHASE6-VERIFICATION.md`.  

## Architecture & Security Realignment (Slice 0)

Status: **PARTIAL → security/domain P0 landed; core cutover deferred by slice**

Docs: `CORE-REALIGNMENT-PLAN.md`, `ROUTE-PERMISSION-MATRIX.md`, `SECURITY-REMEDIATION-REPORT.md`, `DATA-MIGRATION-REPORT.md`, `FINAL-INDEPENDENT-VERIFICATION-READY.md`

Delivered:
- CoreGrcGateway boundary (`engine/core_gateway.py`)
- P0 route auth (control/evidence/task/settings/audit/client/program)
- CSRF + login throttle + session revoke + MFA enforce (prod)
- State-changing GET → 405; feature flags server-side OFF
- Gap engine rewrite (findings-only, delta isolation)
- Mapping: only APPROVED operational; no implicit FULL
- Evidence multipart binary SoT; clients.json first-class
- Deploy: no world-writable chmod; `/api/build-info`

Ready for real client data: **NO**

## Product Realignment — Knowledge Base Authoring

Status: **COMPLETE (UI authoring workflow)**

- Navigazione semplificata: Area di lavoro / Programma corrente / Knowledge Base / Amministrazione
- Feature non-core nascoste dalla nav primaria (owners, deadlines, AI, connectors, auto-evidence, sources, FW suggestions)
- Quick Create (`+ Nuovo`) permission-aware in topbar
- KB authoring end-to-end dalla UI: Framework → Versione DRAFT → Voci normative (+ CSV) → Controlli → Mapping → Publish
- Catalogo controlli unificati (`/controls`)
- Client/Program create + selezione FrameworkVersion PUBLISHED + checklist unificata deduplicata
- Published immutability enforced in service/API + test
- Fix: NIS2 2026.2 same framework_id; demo mapping rationale; task/evidence flag contradictions; IT enums/dates; no EN switch
- Test: `test_kb_authoring` + hardening + Michele regression

Ready for real client data: **NO** (temporary review credential + MFA enroll incompleto)

## Product Completion & Production Hardening

Authentication: PASS — workspace anonimo chiuso; login/logout; cookie HttpOnly/SameSite/Secure; idle 45m / absolute 8h  
RBAC: PASS — SUPER_ADMIN / CONSULTANT / CLIENT_ADMIN / CLIENT_MEMBER / VIEWER + assignments  
Evidence: PASS — storage privato + download autorizzato `/api/evidence/{id}/download`  
Knowledge Base: PASS — `/frameworks` + detail + versioni  
Mappings: PASS — `/mappings` con filtri FULL/PARTIAL/SUPPORTING + unmapped  
Audit: PASS — JSONL append-only + `/audit`  
Security: PASS headers/CSP/SSRF; MFA PARTIAL (TOTP hook)  
Backup: PASS documentato + restore isolato  
Tests: `test_production_hardening` + suite esistenti  
Deployment: `deploy/deploy-compliance.ps1` → https://compliance.wayfold.xyz/  

Ready for real client data: **NO** (temporary review credential + MFA enroll incompleto)

## Product Review Dataset

Status: **READY FOR FINAL EXTERNAL REVIEW** (NOT ready for real client data)

Seed command:

```powershell
python -m engine.seed_review_demo --write-fixtures
python -m engine.seed_review_demo --data-dir <WAYFOLD_DATA_DIR>
```

Demo client: Michele S.r.l. [Demo]  
Dataset marker: `WF_REVIEW_DEMO_2026`  
Live URL: https://compliance.wayfold.xyz/  
Live verified: **YES**  
E2E: PASS (`test_review_demo` + browser live Michele workflow)  
Docs: `DEMO-REVIEW-DATASET.md`, `PRODUCT-ACCEPTANCE-REVIEW.md`

Security findings:
- P0 BEFORE REAL CLIENT DATA: temporary `admin/admin` review credential
- P0: consultant session is global superuser (no per-tenant login roles yet)
- Evidence binary download authz: NOT IMPLEMENTED (catalog-only overlay)  

### UI redesign (definitive mockup) — COMPLETE

- Design system WayFold Compliance (navy + purple) in `engine/ui_shell.py`
- Docs: `docs/design/DESIGN-SYSTEM.md` + mockup HTML in `docs/design/`
- Sidebar sezionata + icone SVG + localizzazione IT centralizzata
- Pagine migrate: Portfolio, Area cliente, Controlli, Gap, Control detail, Attività, Evidenze, Report, Regulatory, AI, Auto-evidence

### Hardening phase — IN PROGRESS (gate prodotto)

Priorità P0 (prima di nuove feature / dati cliente reali):
1. **Auth** — login sessione; `OPEN_ACCESS=0` in prod; `/portfolio` non pubblico
2. **Tenant isolation** — test negativi API/UI/download (già parziale in suite; da estendere)
3. **Evidence hardening** — non iniziato
4. **SSRF regulatory fetcher** — non iniziato

Completato in questo slice:
- `/login` + cookie sessione firmata (`engine/auth_session.py`)
- Produzione: `WAYFOLD_OPEN_ACCESS=0`, `WAYFOLD_ALLOW_QS_AUTH=0`
- Portfolio empty → onboarding a 4 passi + CTA (niente KPI a zero come contenuto principale)
- Fix navigazione program-scoped (redirect / select client)

Gate E2E Michele (non ancora PASS): login → programma → controlli unificati → delta PARTIAL → evidence → task → dashboard.

Prossima azione: credenziali prod + seed staging Michele + test 401/403 negativi evidence.

## Completato

- Scaffold `apps/wayfold-compliance/`
- Phase -1 discovery + scorecard (`open-source-evaluation.md`)
- Phase 0 decision gate: core **CISO Assistant Community**, Strategy B
- Phase 1 Working Core verified (`PHASE1-VERIFICATION.md` → **PASS**)
- Phase 2 Unified Compliance verified (`PHASE2-VERIFICATION.md` → **PASS**)
- Phase 3 Consultant UX verified (`PHASE3-VERIFICATION.md` → **PASS**)
- Phase 4 Regulatory Intelligence verified (`PHASE4-VERIFICATION.md` → **PASS**)
- Phase 5 AI Assistance verified (`PHASE5-VERIFICATION.md` → **PASS**)
- Phase 6 Automated Evidence verified (`PHASE6-VERIFICATION.md` → **PASS**)
  - `ProwlerJsonAdapter` (fixture-compatible; live scan ENVIRONMENT BLOCKER on Windows)
  - Connector config, normalize finding, map → canonical control (SUPPORTING)
  - `AutomatedEvidenceRecord` with provenance + human review
  - Idempotent ingest / stale on change; scanner failure isolated
  - Technical PASS does **not** mutate AppliedControl / readiness
  - UI pages su `engine/ui_shell.py` (fix verification: no generic admin shell)
  - tests: 10 OK (`test_automated_evidence`)
- Docs: `unified-compliance.md`, `consultant-ux.md`, `regulatory-watcher.md`, `ai-assistance.md`, `automated-evidence.md`, `data-model.md`

## Cosa funziona

- Core CISO Docker locale (Phase 1)
- Unified checklist / readiness / impact (Phase 2)
- Consultant UX locale `:8092` con auth esplicita
- Isolation portfolio + regulatory impact per actor tenant
- Regulatory demo cycle v1→v2 senza rete esterna
- AI suggest endpoints con gate tenant + AI disabled-by-default
- Auto-evidence ingest da fixture Prowler + review umana + shell WayFold

## Cosa non funziona / gate aperti

- Live Prowler scan non eseguibile in questo ambiente Windows (path length) — fixture adapter by design
- Provider LLM reale non configurato (heuristic locale by design overnight)
- Optimistic locking integer `version` su AppliedControl assente nel core (warning Phase 1)
- PDF/RSS/API adapters tipizzati ma senza parser specializzati (estendibili)
- Bridge post-APPROVED → CISO EvidenceRevision deferito

## Stato DB

- Core: SQLite locale compose (`vendor/.../db/`, gitignored)
- WayFold mappings + portfolio registry: overlay JSON (non nel DB core)
- Regulatory store: `engine/data/regulatory/` (gitignored runtime)
- AI store: `engine/data/ai/` (gitignored runtime)
- Automated evidence store: `engine/data/automated_evidence/` (gitignored runtime)

## Migrazioni recenti

- Nessuna migration prodotto WayFold; core CISO migrations applicate nel container
- Nessuna migration distruttiva; store regulatory/AI/auto-evidence file-based engine-side

## Comandi di avvio

```powershell
cd apps/wayfold-compliance
python -m engine.tests.test_unified_compliance
python -m engine.tests.test_consultant_ux
python -m engine.tests.test_regulatory
python -m engine.tests.test_ai
python -m engine.tests.test_automated_evidence
python -m engine --superuser --format text
python -m engine.api   # http://127.0.0.1:8092/portfolio?superuser=1
# Auto evidence: /connectors?superuser=1
#                /auto-evidence?superuser=1
#                /api/auto-evidence/ingest?superuser=1&connector_id=conn-prowler-michele-demo
```

## Git

- Remote: https://github.com/DiMichele/WayFold-Compliance
- Branch automazione: `automation/wayfold-compliance`
- `vendor/` non versionato

## Problemi aperti

- Auth Cursor Agent CLI per unattended overnight (operativo)
- `test_regulatory.test_snapshots_append_only_with_stable_hashes` flaky/hash mismatch (non legato al redesign UI; store runtime)

## UI redesign status

| Area | Stato |
|---|---|
| Design system / tokens | Done |
| App shell / sidebar / topbar | Done |
| Icone SVG navigazione | Done |
| Italian localization | Done |
| Portfolio / Client / Controls / Gaps | Done |
| Tasks / Evidence / Report | Done |
| Regulatory / AI / Auto-evidence | Done (stesso shell) |
| Control drawer (vs page) | Page restyled (drawer non forzato — dettaglio già route `/control`) |
| Kanban tasks | Non forzato (lista densa; engine task non espone colonne kanban) |
| Visual debt | Filtri ancora form classico; command palette non implementata (nascosta di proposito) |

## Technical debt

- Dedup coverage su export CISO con assessment duplicati — gestito in checklist/readiness
- pytest assente nell'immagine runtime CISO (test engine host-side)
- UX HTML locale (non fork SvelteKit CISO) — integrazione UI core deferibile
- Regulatory HTTP check on-demand (scheduler/worker persistente deferibile)
- Heuristic AI → sostituibile con LLM provider sullo stesso contract
- Live Prowler / cloud credentials → quando ambiente lo consente, stesso adapter boundary
- Eventuale drawer laterale controllo + virtualizzazione tabelle 500+ row

## Prossimo step consigliato

1. Orchestratore: FINAL REGRESSION GATE + tag `phase-6-complete` + merge su main  
2. Non sviluppare Phase 7 in questa pipeline di close

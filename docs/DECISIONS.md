# DECISIONS — WayFold Compliance

## [2026-08-09] Architecture realignment — stop dual GRC core drift

Scelto:
- Confermare Strategy B: CISO Assistant = authoritative GRC core; WayFold = overlay only where STRUCTURALLY MISSING.
- Introduzione `CoreGrcGateway` come boundary stabile; niente accoppiamento diretto UI→ORM/HTTP.
- Slice 0: security + gap/mapping/evidence/task/client fixes sul codice corrente senza big-bang migration.
- KEEP custom: MappingRecord coverage (FULL/PARTIAL/SUPPORTING+delta+review), Regulatory*, AI*, ReportSnapshot, AutomatedEvidence* (flag OFF).
- MIGRATE per slice: users/RBAC, Folder/Perimeter, AppliedControl, Evidence, TaskNode, libraries.
- ProgramSnapshot: DTO / read model / fixture — non secondo core GRC a lungo termine.
- Documentazione verità: nessun PASS su hook (MFA/scan/backup).

Motivazione: review indipendente ha rilevato due GRC core paralleli; continuare la deriva è vietato.

Rivedere se: Slice A–G completate; CISO espone nativamente coverage SUPPORTING+delta.

---

## [2026-08-09] Product realignment — authoring workspace over viewer

Scelto:
- WayFold Compliance è un workspace di authoring Knowledge Base + programmi cliente, non solo un viewer.
- Entità riusate: `FrameworkRecord` + `FrameworkVersionRecord` / `FrameworkRequirement`, `CanonicalControl` (catalog), `MappingRecord` (KB store), `ProgramSnapshot`.
- Navigazione primaria ridotta ai workflow core; AI/connectors/auto-evidence/sources/suggestions restano raggiungibili ma fuori dalla sidebar.
- Lingua prodotto: italiano only (selettore EN rimosso finché non esiste localizzazione EN completa).
- Versioni PUBLISHED immutabili (service+API); edit solo via clone DRAFT → publish.

Motivazione:
- Un amministratore deve costruire il modello senza seed/JSON/codice.
- Framework-specific requirement ≠ controllo unificato; niente duplicazione controlli per framework.

Rivedere se:
- serve persistenza DB dedicata oltre agli overlay JSON;
- MFA enrollment obbligatoria chiude il gate REAL CLIENT DATA.

---

## [2026-08-09] Brand prodotto — solo WayFold Compliance

Scelto:
- Il nome pubblico del prodotto è **WayFold Compliance**.
- Nessuna UI, titolo browser, nginx comment rivolto all’utente, README di prodotto o copy deve presentare il motore GRC OSS (o altri vendor) come brand.
- La home pubblica (`compliance.wayfold.xyz/`) serve l’engine WayFold; l’eventuale admin UI del substrate non è esposta sul dominio prodotto.
- `WAYFOLD_OPEN_ACCESS=1` in produzione finché non esiste login prodotto WayFold.

Motivazione:
- Il core OSS era solo punto di partenza tecnico (Strategy B), non identità di prodotto.
- Allineamento all’ecosistema WayFold (Bills / wayfold.xyz).

---

## [2026-08-09] Core GRC selection — substrate OSS + Strategy B

> Nota brand: questa decisione è storica/tecnica. In UI e messaggi utente usare solo «WayFold Compliance» / «GRC core» / «substrate».

Scelto:
- **Core:** CISO Assistant Community (`intuitem/ciso-assistant-community`)
- **Strategy B:** Existing GRC Core + Wayfold Regulatory / Mapping Engine (servizi esterni via API)

Motivazione:
- Scorecard §111 (vedi `open-source-evaluation.md`): CISO vince sui criteri a peso alto (domain model fit 5, reuse 5, mapping 5, evidence/tasks 5).
- Equivalenze semantiche verificate nel codice (`backend/core/models.py`):
  - `ReferenceControl` ≈ CanonicalControl
  - `AppliedControl` ≈ ControlImplementation
  - `RequirementNode` ≈ Requirement
  - `Folder`/`Perimeter` ≈ Client / program scope (adattabile)
  - `ComplianceAssessment` ≈ assessment multi-framework
- Frameworks sono **dati** (YAML libraries), non codice — allineato a WayFold §103.1.
- API DRF/OpenAPI consente estensioni Wayfold senza fork del motore GRC.
- Regulatory monitoring assente in tutti i candidati → naturalmente **esterno** (Strategy B), non motivo per Strategy C.

Alternative considerate:
- **Probo (Strategy A/B):** Measure-centric, GraphQL/MCP eccellenti; manca layer Requirement/Canonical separato; snapshots compliance rimossi. Runner-up.
- **Unicis (Strategy A):** UX Next.js; frameworks hardcoded in TypeScript; evidence assente — scartato come core (non per preferenza linguaggio).
- **Strategy C (custom GRC):** non giustificata — nessuna capability class 4 strutturale sul dominio core in CISO.

Rivedere se:
- la demo Michele fallisce sul riuso di una singola implementazione su più framework (product blocker);
- emergono limiti di licenza/community incompatibili con uso privato;
- Probo introduce un modello Canonical/Requirement superiore e si rivaluta con nuova decisione.

---

## [2026-08-09] Specialized components roles

Scelto:
- OpenCRE → cross-framework relationships / gap analysis API
- Trestle + OSCAL → import/export / compliance-as-code (non UI)
- Prowler → Phase 6 only

Motivazione:
- Non competono come core; evitano architettura Frankenstein.

Alternative considerate:
- Incorporare OpenCRE dentro il DB CISO subito — deferito a Phase 2+.

Rivedere se:
- Phase 2 unified mapping richiede CRE graph operativo.

---

## [2026-08-09] Phase 2 mapping overlay outside CISO DB

Scelto:
- WayFold `MappingRecord` (FULL / PARTIAL / SUPPORTING + `uncovered_delta` + review_status) come overlay JSON / `ProgramSnapshot` nel package `apps/wayfold-compliance/engine/`.
- Checklist/readiness/impact come application services puri + bridge opzionale ORM CISO.
- UI Phase 2 minima: tabella HTML/JSON su `engine.api` (porta 8092), senza fork del frontend SvelteKit.

Motivazione:
- CISO espone già `ReferenceControl`/`AppliedControl` e req↔req `RequirementMapping` (FULL/PARTIAL), ma non il modello req↔canonical con SUPPORTING + delta richiesto da WayFold §19/§34.
- Strategy B: estendere via engine esterno evita fork del core e duplicazione auth/evidence/tasks.
- UI consultant densa completa è Phase 3; Phase 2 consegna la capability + vista professionale minima.

Alternative considerate:
- Patch diretta ai modelli Django CISO (fork) — scartata per costo upgrade.
- Solo `RequirementMapping` req↔req — insufficiente per checklist basata su CanonicalControl.

Rivedere se:
- CISO introduce nativamente req↔control coverage con SUPPORTING;
- serve persistenza DB dedicata engine prima di Phase 4.

---

## [2026-08-09] Phase 2 authz default-deny on engine endpoints

Scelto:
- API (`engine.api`) e CLI richiedono esplicitamente `--superuser` / `superuser=1` **oppure** `actor_tenants` / `--actor-tenants`.
- Empty actor set non implica più superuser.

Motivazione:
- Verification Phase 2: il bypass `is_superuser or not actor_tenants` violava tenant isolation + RBAC sui nuovi endpoint.

Alternative considerate:
- Token sessioni CISO pass-through subito — deferito; overlay gate resta fino a integrazione prod API.

Rivedere se:
- l'engine viene esposto dietro lo stesso IAM CISO in produzione.

---

## [2026-08-09] Phase 3 Consultant UX on engine HTML/JSON (not CISO fork)

Scelto:
- Portfolio / Client / Gaps / Owners / Deadlines / Evidence / Tasks / Reports come servizi + dense HTML su `engine.api` (:8092), riusando checklist/readiness/impact Phase 2 e snapshot programmi (Michele + Alfa registry).

Motivazione:
- Strategy B: UX consulente quotidiana senza fork del frontend SvelteKit; evidence/tasks/owners restano semanticamente quelli del core.
- Filtri e report operano su dati pinned del programma, non su KB globale.

Alternative considerate:
- Patch UI CISO (fork) — scartata per costo upgrade.
- Nuovo SPA separato — overkill per Phase 3 MVP giornaliero.

Rivedere se:
- serve embedding ufficiale nel frontend CISO o autenticazione SSO condivisa.

---

## [2026-08-09] Phase 4 Regulatory store outside CISO DB

Scelto:
- Source / SourceSnapshot / RegulatoryChange / FrameworkUpdateSuggestion persistiti in `engine/data/regulatory/` (JSON + blobs) nel package WayFold Engine.
- Pipeline deterministica `fetch → normalize → hash → compare → diff → change → impact`; review umana obbligatoria per ACCEPTED/IGNORED.
- Cosmetic HTML (normalized hash invariato) non apre change.
- Framework update = `FrameworkUpdateSuggestion` (CLONE_DRAFT) — mai publish/silent mutate delle library CISO.

Motivazione:
- Strategy B e confini DB: regulatory monitoring assente nel core; non forkare CISO per watcher.
- Demo/test con `fixture://` locale evitano dipendenza da siti esterni.
- Allineato a §52–§56 e §103.12 (watcher non muta silenziosamente framework/client).

Alternative considerate:
- Tabelle Django nel core CISO — scartate (fork + coupling).
- Scraper CSS-selector monolitico — scartato; adapter per content-type.

Rivedere se:
- serve DB PostgreSQL dedicato engine in produzione;
- Phase 5 AI analysis richiede coda/worker persistente oltre al check on-demand.

---

## [2026-08-09] Phase 5 AI via AIProvider + heuristic default

Scelto:
- `AIAssistanceService` + protocol `AIProvider` in `engine/ai/`.
- Default provider: `HeuristicAIProvider` (deterministico, no API key / no LLM esterno).
- `TenantAISettings.ai_processing_enabled = false` di default.
- Ogni output è `AISuggestion` con `AI_SUGGESTED`; approve/reject umano obbligatorio.
- Nessuna auto-applicazione a mapping/baseline/compliance CISO.

Motivazione:
- Master plan §57–§62: AI suggerisce, umano approva; prodotto utile senza AI.
- Overnight senza credenziali prodotto / senza secret LLM.
- Strategy B: store AI engine-side (`engine/data/ai/`), non fork CISO.

Alternative considerate:
- Chiamate OpenAI dirette da API handler — scartate (accoppiamento + secret).
- AI sempre on — viola default-off tenant control.

Rivedere se:
- si configura un provider LLM reale dietro lo stesso contract;
- serve coda/worker asincrona per analisi lunghe.

---

## [2026-08-09] Regulatory client impact tenant-filtered

Scelto:
- Sources / Changes inbox restano KB-level autenticati (fonte normativa globale).
- `ClientImpactReport` è filtrato server-side per `actor_tenant_ids` (fail-closed se né superuser né actor).

Motivazione:
- Verification Phase 4: senza filtro, un actor Michele poteva teoricamente vedere row Alfa su source multi-tenant.
- Allineato a tenant isolation Phase 2–3 senza trasformare le fonti ufficiali in dati per-tenant.

Alternative considerate:
- Nascondere l’intera inbox regulatory ai non-superuser — troppo restrittivo per il workflow consulente.
- Fidarsi del fatto che i link source colpiscano un solo tenant — insufficiente.

Rivedere se:
- le Sources diventano tenant-owned (multi-tenant SaaS pubblico).

---

## [2026-08-09] Production deploy in overnight pipeline

Scelto:
- Dopo Phase 6 PASS + final regression + merge su `main`, l’overnight esegue **autoDeploy** su VPS:
  - host `wayfold@167.233.121.159`
  - path `/home/wayfold/apps/wayfold-compliance`
  - dominio `https://compliance.wayfold.xyz`
  - script `deploy/deploy-compliance.ps1` (+ nginx/TLS via `setup-nginx-tls.sh`)
- Stack: substrate GRC (immagini ghcr) + engine WayFold Compliance su `:18092` come UI pubblica `/`
- Nessun deploy del prodotto viaggi (`deploy/deploy.ps1`) da questa pipeline.

Motivazione:
- DNS già punta al VPS; senza deploy+cert il browser mostra `ERR_CERT_COMMON_NAME_INVALID` (cert di bills).

Rivedere se:
- si separa un repo/deploy host dedicato.

---

## [2026-08-09] Visual language — allineamento ecosistema WayFold (Bills)

> **SUPERSEDED** da «WayFold Compliance definitive design system» (sotto). Storico: l’UI era allineata a Bills (terracotta/sage/Jost).

Scelto (storico):
- Palette Bills charcoal/sage/terracotta; tipografia Jost/Inter/DM Mono via `engine/ui_shell.py`.

---

## [2026-08-09] WayFold Compliance definitive design system

Scelto:
- Source of truth visuale: `docs/design/wayfold-compliance-definitive-mockup.html` + `docs/design/DESIGN-SYSTEM.md`.
- Identità: **navy sidebar** `#101522` · superfici chiare `#f5f7fb`/`#fff` · accento viola WayFold `#675cf2` · Inter · densità desktop-first.
- Shell: sidebar scura sezionata + topbar sticky + page header operativo (no fake search/CTA).
- Icone: solo SVG centralizzate (`engine/ui_icons.py`).
- Lingua UI default: **italiano** (`engine/i18n.py`); status/mapping/priority via `engine/ui_labels.py`.
- Dark mode content: non implementato (sidebar scura fa parte del light design).
- Nessun fork del frontend SvelteKit del core; resta Strategy B overlay HTML.

Motivazione:
- Mockup definitivo Compliance è più adatto al lavoro GRC quotidiano (alta densità, data tables) rispetto al look warm di Bills.
- Coerenza ecosistema via brand WayFold + viola, senza template SaaS generico.

Rivedere se:
- nasce un package design-system monorepo condiviso Bills/Compliance.

---

## [2026-08-09] Phase 6 Automated Evidence via Prowler JSON adapter + fixture

Scelto:
- Package `engine/automated_evidence/` con boundary `ScannerAdapter` → `NormalizedFinding` → mapping SUPPORTING → `AutomatedEvidenceRecord`.
- Adapter **Prowler JSON** (fixture-compatible). Live Prowler scan non eseguito qui (ENVIRONMENT BLOCKER Windows path length, già in open-source-evaluation).
- Evidence type semantico `EXTERNAL_REFERENCE` con provenance; store engine-side `engine/data/automated_evidence/`.
- Human review obbligatoria; technical PASS **non** muta `AppliedControl` / readiness / baseline.
- Credenziali solo come `credential_ref` (nome env var), mai inline nel codice/store.

Motivazione:
- DECISIONS precedenti: Prowler = Phase 6 specialized component, non core.
- Master plan §98 + phase-06-develop: non inventare un nuovo CSPM; non trasformare la fase in progetto cloud-security infinito.
- Strategy B: riuso concetto Evidence del core senza fork DB; overnight senza secret cloud.

Alternative considerate:
- Eseguire Prowler live in CI overnight — bloccato da environment Windows.
- Scrivere findings direttamente nelle tabelle Evidence CISO — scartato (coupling + silent mutate).
- Auto-set status IMPLEMENTED su PASS tecnico — viola Unified Compliance (SUPPORTING only).

Rivedere se:
- ambiente Linux/CI consente export Prowler reale sullo stesso adapter;
- serve bridge API CISO per materializzare EvidenceRevision dopo APPROVED.

---

## [2026-08-09] Nessun credential di accesso prodotto (temporaneo)

> **SUPERSEDED** da «Hardening gate — auth before features» (sotto).

---

## [2026-08-09] Hardening gate — auth before features

Scelto:
- **Stop feature race** (Phase 3/4/5/6 UI polish senza fondamenta). Nessuna nuova fase “completa” finché non passa il gate Michele E2E autenticato.
- Produzione: `WAYFOLD_OPEN_ACCESS=0`, `WAYFOLD_ALLOW_QS_AUTH=0`.
- Route pubbliche: `/login`, `/logout`, `/healthz`, `/api/health`. Tutto il resto richiede sessione cookie firmata.
- Credenziali consulente in `data/engine/.auth.env` (non in git); query `?superuser=1` **disabilitata** in prod.
- Empty state Portfolio = onboarding operativo (non quattro zeri).
- Gate E2E obbligatorio: login → Michele → checklist → CTRL con FULL/PARTIAL/delta → evidence → task → readiness coerente + isolamento tenant.

Motivazione:
- Workspace pubblico + empty state vuoto + assenza workflow dimostrabile = rischio security e prodotto.
- Review prodotto: P0 auth / tenant isolation / evidence / SSRF prima di AI/Prowler/visualizzazioni.

Non ancora in questo gate (P0 residuo):
- RBAC multi-ruolo completo
- Evidence private storage + signed URL
- SSRF hardening fetcher normativo
- Audit log prodotto

Rivedere quando:
- serve IdP/SSO reale o multi-utente consulente;
- si apre staging `compliance-dev` con seed Michele.

---

## [2026-08-09] Authentication / authorization boundary (engine)

Scelto:
- Sessione cookie firmata con `role` + `tenant_ids` + idle/absolute timeout.
- RBAC prodotto su ruoli `SUPER_ADMIN|CONSULTANT|CLIENT_ADMIN|CLIENT_MEMBER|VIEWER`.
- `SUPER_ADMIN` bypass tenant; `CONSULTANT` limitato da `consultant_assignments.json`.
- Credenziale env temporanea = SUPER_ADMIN esplicita (`TEMPORARY REVIEW CREDENTIAL`), non hardcoded.

Motivazione: chiudere il modello “login = superuser globale” prima del review esterno finale.

---

## [2026-08-09] Evidence download strategy

Scelto:
- Filesystem privato sotto `WAYFOLD_DATA_DIR/evidence/{tenant}/{id}/`.
- Stream solo tramite middleware authz (`/api/evidence/{id}/download`).
- Nessun URL statico pubblico; signed URL object-storage deferibile.

---

## [2026-08-09] Audit event model

Scelto:
- Append-only JSONL `audit/events.jsonl` con scrubbing secret.
- UI `/audit` filtrabile; eventi minimi prodotto (login, control, evidence, mapping, report, AI).

---

## [2026-08-09] Report snapshot architecture

Scelto:
- Snapshot JSON persistiti in `report_snapshots/` al generate-time.
- Indipendenti da mutazioni successive del ProgramSnapshot.

---

## [2026-08-09] MFA mechanism

Scelto:
- TOTP puro Python (`engine/mfa.py`) senza dipendenze esterne.
- Enforcement enroll UI completo = PARTIAL / blocker soft prima di REAL CLIENT DATA.
- Temporary review credential può bypassare MFA enrolled.

---

## [2026-08-09] CSP strategy

Scelto:
- CSP compatibile app HTML attuale: `default-src 'self'`, fonts Google, `style-src`/`script-src` con `'unsafe-inline'` (no `'unsafe-eval'`).
- `frame-ancestors 'self'` + headers nginx HSTS/XCTO/Referrer/Permissions-Policy.

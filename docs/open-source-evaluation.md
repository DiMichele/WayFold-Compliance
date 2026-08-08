# Open Source Evaluation — WayFold Compliance

Stato: **completata** (Phase -1) — revisione clonata 2026-08-09 (shallow clone).

## Classificazione repository

```text
CORE CANDIDATES
├── CISO Assistant  (intuitem/ciso-assistant-community)
├── Probo           (getprobo/probo)
└── Unicis          (UnicisTech/unicis-platform-ce)

SPECIALIZED COMPONENTS
├── OpenCRE         → mappings / knowledge graph
├── Trestle         → compliance-as-code / OSCAL tooling
├── OSCAL           → schema / interoperability
└── Prowler         → future technical evidence (Phase 6)
```

Clone locali: `apps/wayfold-compliance/vendor/` (gitignored).

**Environment note — Prowler:** clone fallito parzialmente su Windows (`Filename too long` / checkout). Documentato come **ENVIRONMENT BLOCKER**, non product blocker. Analisi Prowler limitata a README/architettura nota; non usato come core.

---

## Capability matrix

Valori: `AVAILABLE` | `PARTIAL` | `MISSING`

| Capability | Required | CISO Assistant | Probo | OpenCRE | Unicis | Best |
|---|---|---|---|---|---|---|
| Clients | YES | PARTIAL (`Folder` DOMAIN / `Perimeter`; no `Client`) | AVAILABLE (`Organization`) | MISSING | AVAILABLE (`Team`) | Probo / Unicis |
| Multi-tenancy | YES | AVAILABLE (folder-scoped RBAC) | AVAILABLE (`tenant_id` + Scoper) | MISSING | AVAILABLE (`Team`) | CISO / Probo |
| Frameworks | YES | AVAILABLE (`Framework` + `LoadedLibrary`) | AVAILABLE (`Framework`) | PARTIAL (standards as Nodes) | AVAILABLE (static TS catalogs) | CISO |
| Framework versions | YES | PARTIAL (`LoadedLibrary.version`; no `FrameworkVersion` entity) | MISSING | PARTIAL (Node.version) | PARTIAL (ISO 2013 vs 2022 as separate keys) | CISO |
| Requirements | YES | AVAILABLE (`RequirementNode`) | PARTIAL (`Control` = per-framework requirement) | AVAILABLE (CRE + Node sections) | PARTIAL (IDs + i18n) | CISO |
| Requirement hierarchy | YES | AVAILABLE (`parent_urn`, `order_id`) | PARTIAL (`SectionTitle`) | AVAILABLE (CRE links) | PARTIAL (sections in TS) | CISO |
| Common controls | YES | AVAILABLE (`ReferenceControl`) | PARTIAL (`Measure` reusable; no separate canonical catalog) | PARTIAL (CRE as semantic hub) | MISSING | CISO |
| Mappings | YES | AVAILABLE (`RequirementNode.reference_controls`, RA↔AC) | AVAILABLE (`controls_measures`) | AVAILABLE (CRE↔Node) | AVAILABLE (`framework-mappings.ts`) | CISO |
| Cross-framework mapping | YES | AVAILABLE (`RequirementMapping` / `RequirementMappingSet`) | PARTIAL (via Measure↔Control↔Framework) | AVAILABLE (core purpose) | AVAILABLE (matrix from CISO YAML) | CISO / OpenCRE |
| Client implementation | YES | AVAILABLE (`AppliedControl`) | AVAILABLE (`Measure.State` + evidence/tasks) | MISSING | PARTIAL (JSON status on Team) | CISO |
| Evidence | YES | AVAILABLE (`Evidence`, `EvidenceRevision`) | AVAILABLE (`Evidence`) | MISSING | PARTIAL (`Attachment` on Task only) | CISO / Probo |
| Tasks | YES | AVAILABLE (`TaskTemplate` / `TaskNode` + AC workflow) | AVAILABLE (`Task`) | MISSING | AVAILABLE (`Task`) | CISO / Probo |
| Assessments | YES | AVAILABLE (`ComplianceAssessment`, `RequirementAssessment`) | PARTIAL (`Audit` + SoA; no req-level CA) | PARTIAL (gap analysis) | PARTIAL (PIA/TIA/RPA only) | CISO |
| Snapshots | YES | PARTIAL (`FrameworkSnapshot` trust-center oriented) | MISSING (dropped in migrations 20260527) | MISSING | MISSING | CISO |
| API | YES | AVAILABLE (DRF + OpenAPI) | AVAILABLE (GraphQL + MCP + CLI) | AVAILABLE (REST read-only) | AVAILABLE (Next API + OpenAPI) | CISO / Probo |
| RBAC | YES | AVAILABLE (`Role` / `RoleAssignment` folder-scoped) | AVAILABLE (IAM policies) | MISSING | AVAILABLE (Team roles + permissions) | CISO / Probo |
| Dashboard | YES | AVAILABLE (frontend SvelteKit) | AVAILABLE (React console) | PARTIAL | AVAILABLE | CISO / Probo |
| Reporting | YES | AVAILABLE (export / analytics) | AVAILABLE (export jobs) | PARTIAL (CSV / OSCAL) | PARTIAL | CISO |
| Import/export | YES | AVAILABLE (YAML libraries, data wizard) | AVAILABLE (framework import/export) | AVAILABLE (upstream sync) | AVAILABLE (module import) | CISO |
| Regulatory monitoring | YES | MISSING | MISSING | MISSING | MISSING | none (CUSTOM WAYFOLD) |
| Extensibility | YES | AVAILABLE (API-first, libraries as data) | AVAILABLE (GraphQL/MCP) | AVAILABLE (API for mappings) | PARTIAL (hardcoded frameworks conflict with WayFold §103.1) | CISO |

### Evidenze path (CORE)

**CISO Assistant** (`vendor/ciso-assistant-community`):

- `backend/core/models.py` — `ReferenceControl` (~2656), `RequirementNode` (~2946), `RequirementMapping` (~3387), `Perimeter` (~3465), `AppliedControl` (~5570), `ComplianceAssessment` (~7303), `Evidence` (~5048)
- `backend/iam/models.py` — `Folder`, `Role`, `RoleAssignment`
- `backend/core/urls.py` — DRF router
- `docker-compose.yml`, `backend/Dockerfile`

**Probo** (`vendor/probo`):

- `pkg/coredata/organization.go`, `measure.go`, `control.go`, `framework.go`, `evidence.go`, `task.go`, `control_mesure.go`
- `pkg/server/api/console/v1/graphql/*.graphql`
- `pkg/server/api/mcp/v1/specification.yaml`
- `compose.yaml`, `GNUmakefile`

**Unicis** (`vendor/unicis-platform-ce`):

- `prisma/schema.prisma` — Team/Task/Attachment; **no** Framework/Control/Evidence tables
- `lib/csc/frameworks/*.ts` — frameworks as code
- `lib/csc/framework-mappings.ts` — mapping matrix (generated from CISO Assistant YAML)
- `lib/permissions.ts`, `pages/api/teams/[slug]/csc/`

### Specialized (ruolo, non scorecard core)

| Component | Role | Key paths |
|---|---|---|
| OpenCRE | Cross-framework CRE graph / gap analysis | `application/database/db.py`, `application/defs/cre_defs.py`, `docs/api/openapi.yaml` |
| Trestle | OSCAL validate/transform/Git workflow | `trestle/`, `release-schemas/` |
| OSCAL | Schema source of truth | `src/metaschema/`, `src/specifications/` |
| Prowler | Future automated technical evidence | ENVIRONMENT BLOCKER on Windows path length; defer Phase 6 |

---

## Scorecard criteri §111

Punteggio 1–5. **Non** decide matematicamente il vincitore; ogni cella cita evidenza codice.

| Criterio | Peso | CISO Assistant | Probo | Unicis |
|---|---:|---:|---:|---:|
| Domain model fit | 10 | **5** — `ReferenceControl`/`AppliedControl`/`RequirementNode`/`ComplianceAssessment` in `backend/core/models.py` allineati al layering WayFold | **4** — `Measure`→N `Control`→`Framework` forte (`measure.go`, `control_mesure.go`); manca layer Requirement/Canonical separato | **2** — GRC in JSON/`lib/csc` TS; nessun modello normalizzato Framework/Control/Evidence in Prisma |
| Reuse | 9 | **5** — library YAML, assessment, evidence, tasks, RBAC, mapping già operativi | **4** — GRC lifecycle ampio + MCP/CLI; meno library framework “da dati” rispetto a CISO | **3** — task/auth/CSC UI riusabili; mapping già derivato da CISO; evidence assente |
| API/extensibility | 8 | **5** — DRF + OpenAPI (`ciso_assistant/urls.py`, `core/urls.py`) | **5** — GraphQL + MCP 270+ + CLI (`pkg/server/api`) | **4** — REST OpenAPI + MCP server; dominio meno estendibile perché frameworks hardcoded |
| Maintainability | 7 | **4** — codebase grande Django/Svelte ma community attiva e librerie come dati | **4** — Go tipizzato, molte migrazioni; stack solido ma pesante | **3** — Next.js familiare ma dominio in JSON rischia debito |
| Multi-client | 7 | **4** — `Folder` DOMAIN + `Perimeter` + folder RBAC; Client MSP da modellare come Folder/Perimeter | **4** — `Organization`+`tenant_id` chiaro; MSP portfolio da costruire sopra | **4** — `Team` multi-workspace; non MSP client hierarchy |
| Mapping | 7 | **5** — req↔ref control, RA↔applied, `RequirementMappingSet` | **4** — measure↔control; cross-framework indiretto | **4** — matrix ricca ma statica (`framework-mappings.ts`) |
| Evidence/tasks | 6 | **5** — `Evidence`/`EvidenceRevision` + `TaskNode` + AC status/ETA | **5** — `Evidence` + `Task` su Measure | **3** — Task forti; Evidence solo Attachment |
| Deploy | 5 | **4** — `docker-compose.yml` ufficiale | **4** — `compose.yaml` + Make | **4** — tipico Next/Prisma Docker |
| UX | 3 | **3** — SvelteKit funzionale; non consultant-portfolio-first | **4** — console React moderna | **4** — UX CSC/task buona |
| Language preference | 1 | **3** — Python/Django (ok per GRC) | **3** — Go (ok) | **4** — TS/Next allineato a preferenza WayFold new services |

### Lettura scorecard (non automatica)

- **CISO Assistant** domina su domain model, mapping, assessment, common controls, library-as-data — criteri a peso alto.
- **Probo** è il runner-up più vicino sul concetto “implementa una misura una volta”; gap su Requirement/Canonical layer e snapshot.
- **Unicis** ha UX/TS attraenti ma viola il principio WayFold “frameworks are data, never hardcoded”; evidence/assessment strutturalmente deboli → **non core**.

**Language preference non ribalta** la scelta: Unicis non vince nonostante Next.js.

---

## Equivalenze semantiche (CISO → WayFold)

| WayFold | CISO Assistant | Classe |
|---|---|---|
| CanonicalControl | ReferenceControl | CAPABILITY PRESENTE |
| ControlImplementation | AppliedControl | CAPABILITY PRESENTE |
| Requirement | RequirementNode | CAPABILITY PRESENTE (rename) |
| Client | Folder(DOMAIN) / Perimeter | CAPABILITY ADATTABILE |
| ComplianceProgram | Campaign + ComplianceAssessment (+ multi-framework UX) | CAPABILITY ADATTABILE |
| FrameworkVersion | LoadedLibrary.version + pin via Framework.library | CAPABILITY ADATTABILE |
| Unified checklist | Multi-CA + shared AppliedControl | CAPABILITY ADATTABILE (UX) |
| Regulatory watcher | — | CAPABILITY ESTERNA / CUSTOM |

---

## Decision gate result

Vedere [`DECISIONS.md`](DECISIONS.md) e [`PHASE0-RECOMMENDATION.md`](PHASE0-RECOMMENDATION.md).

**Raccomandazione preliminare (pre-run):** CISO Assistant come GRC core; Strategy B (core + Wayfold Regulatory Engine). Probo secondo classificato — run del secondo **non** obbligatorio salvo dubbio residuo post-demo.

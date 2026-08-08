# Source Reuse Plan — WayFold Compliance

Stato: **completato** post decision gate (core: CISO Assistant, Strategy B).

Per ogni voce: project / module / purpose / integration / reason.

---

## REUSE AS-IS

| Project | Module / file | Purpose | Integration | Reason |
|---|---|---|---|---|
| CISO Assistant | `backend/core/models.py` — Framework, RequirementNode, LoadedLibrary | Framework engine as data | Keep as GRC core DB | Frameworks never hardcoded |
| CISO Assistant | `backend/library/` + YAML libraries | Import/version library content | Core runtime | Already supports custom frameworks |
| CISO Assistant | `ReferenceControl`, `AppliedControl` | Canonical + client implementation | Map semantically to WayFold names in UX/docs | Exact domain fit |
| CISO Assistant | `ComplianceAssessment`, `RequirementAssessment` | Assessment engine | Core | Multi-framework assessments exist |
| CISO Assistant | `Evidence`, `EvidenceRevision` | Evidence store | Core | Do not rebuild |
| CISO Assistant | `TaskTemplate`, `TaskNode`, AppliedControl status/ETA | Remediation / tasks | Core | Do not rebuild |
| CISO Assistant | `backend/iam/` — Folder, Role, RoleAssignment, User | AuthN/Z + tenancy scope | Core | Do not rebuild auth |
| CISO Assistant | `Perimeter`, Folder DOMAIN | Client / program scope proxies | Core + light UX naming | Sufficient model |
| CISO Assistant | DRF API + OpenAPI | External extension boundary | Strategy B API consumer | Wayfold engine talks to core via API |
| CISO Assistant | Docker compose stack | Deploy baseline | Adapt only ingress/domain | Proven path |

---

## ADAPT

| Project | Module | Purpose | Integration | Reason |
|---|---|---|---|---|
| CISO Assistant | Multi-assessment UX | Unified checklist across frameworks | Frontend extension or Wayfold overlay | Model supports shared AppliedControl; UX not consultant-first |
| CISO Assistant | Folder/Perimeter naming | Client + ComplianceProgram mental model | Labels, views, optional thin wrapper API | Semantic rename, not new engine |
| CISO Assistant | LoadedLibrary.version | FrameworkVersion publish/pin UX | Workflow + docs + maybe metadata fields | Entity exists as library version; Wayfold wants explicit pin UX |
| CISO Assistant | Dashboard | Portfolio multi-client consultant view | New views on existing API | Capability PRESENT at API; UX ADAPTABLE |
| CISO Assistant | RequirementMapping confidence/review | Mapping review workflow | Extra fields / status if missing | Core mapping exists; Wayfold wants DRAFT/AI/HUMAN review states |

---

## REIMPLEMENT CONCEPT

| Project | Concept | Purpose | Strategy | Reason |
|---|---|---|---|---|
| Probo | Measure ↔ multi Control | Same idea as AppliedControl covering multi-framework | Prefer CISO AppliedControl+ReferenceControl | Concept already covered by chosen core |
| Unicis | CSC mapping matrix UX | Cross-framework matrix | Inspire UX only; data from CISO/OpenCRE | Unicis matrix sourced from CISO YAML anyway |
| OpenCRE | CRE as hub | Requirement↔Requirement relationships | Import/sync into Wayfold mapping intelligence | Keep as specialized service, not rewrite CRE |

---

## DO NOT USE (as core)

| Project | Why |
|---|---|
| Unicis as GRC core | Frameworks hardcoded in TS; Evidence/Assessment structurally weak; violates WayFold §103.1 |
| Probo as primary core | Strong runner-up but weaker Requirement/Canonical layer vs CISO; second only if CISO demo fails product-wise |
| Prowler (now) | Phase 6 only; Windows path ENVIRONMENT BLOCKER |
| Trestle/OSCAL as UI | Tooling/format only |

---

## CUSTOM WAYFOLD

| Component | Class | Reason |
|---|---|---|
| Regulatory watcher (sources, fetch, snapshot, hash, diff) | CAPABILITY ESTERNA | Missing in all cores |
| Client-impact engine | CAPABILITY ESTERNA | Missing |
| Control ROI | CAPABILITY ESTERNA | Missing |
| Advanced mapping intelligence (+ optional AI suggest) | CAPABILITY ESTERNA | Core has mapping; intelligence layer is Wayfold |
| OpenCRE bridge service | SPECIALIZED | Cross-framework CRE relationships via API |
| OSCAL import/export via Trestle | SPECIALIZED | Interoperability |
| Portfolio / Gap / Deadline consultant UX | CAPABILITY ADATTABILE → may ship as Wayfold UI on CISO API | Consultant workflow priority |

---

## DO NOT BUILD (covered by core)

- Auth / session / RBAC
- Evidence engine
- Task / remediation engine
- Generic GRC backend (frameworks, requirements, assessments, controls)
- Multi-tenancy primitives (reuse Folder/Perimeter)

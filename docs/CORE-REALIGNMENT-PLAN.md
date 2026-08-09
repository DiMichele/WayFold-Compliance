# CORE REALIGNMENT PLAN — WayFold Compliance

Date: 2026-08-09  
Authoritative repo: `DiMichele/WayFold` → `apps/wayfold-compliance/`  
Starting SHA (declared): `dab74ce204fcbfffa6e58a6d4942f1f27c0e1feb`  
Strategy: **B** — CISO Assistant Community as GRC core + WayFold extensions only where structurally missing.

## Target architecture

```text
WayFold UI / UnifiedComplianceService
            │
            ▼
      CoreGrcGateway   ← stable application boundary
            │
            ▼
 CISO Assistant (User, RoleAssignment, Folder/Perimeter,
                 ComplianceAssessment, LoadedLibrary/Framework,
                 RequirementNode, ReferenceControl, AppliedControl,
                 Evidence/EvidenceRevision, TaskNode)
            │
            ▼
 WayFold overlay (ONLY structurally missing):
   MappingRecord (FULL/PARTIAL/SUPPORTING + delta + review)
   RegulatorySource / SourceSnapshot / RegulatoryChange
   AISuggestion / TenantAISettings
   ReportSnapshot
   Feature flags / product UX
```

ProgramSnapshot becomes: **DTO / read model / report snapshot / test fixture** — not mutable operational SoT after cutover.

## Classification legend

| Class | Meaning |
|---|---|
| PRESENT | Core already provides capability |
| ADAPTABLE | Core close; thin adapter OK |
| EXTERNAL | Intentionally outside core (Strategy B) |
| STRUCTURALLY MISSING | Justify WayFold parallel model |

| Action | Meaning |
|---|---|
| KEEP | Remain WayFold-owned |
| MIGRATE | Move ops to CISO via gateway |
| DELETE | Remove after migration |

---

## Entity / store matrix

| CURRENT WAYFOLD ENTITY/STORE | CURRENT FILE | CISO CORE EQUIVALENT | REUSE? | CLASS | MIGRATION STRATEGY | KEEP/MIGRATE/DELETE | RISK | TEST |
|---|---|---|---|---|---|---|---|---|
| UserRecord / users.json | `engine/users.py` | `iam.models.User` | YES | PRESENT | Slice A: auth against CISO; dual-read then cutover | MIGRATE | Session/credential break | `SEC-AUTH-*`, login E2E |
| Role / permissions | `engine/rbac.py` | `Role`, `RoleAssignment` | ADAPT | ADAPTABLE | Map SUPER_ADMIN/CONSULTANT/CLIENT_* → folder-scoped RoleAssignment; keep product permission names as facade | MIGRATE | Over/under-privilege | route permission matrix |
| Cookie session | `engine/auth_session.py` | Django session / IAM | YES | PRESENT | Prefer CISO session; until then harden custom (secret fail-closed, revoke, CSRF) | MIGRATE (interim KEEP hardened) | Prod secret fallback | `SEC-SESSION-*` |
| AuthContext / authz gate | `engine/authz.py` | Folder RBAC | YES | ADAPTABLE | Keep fail-closed gate calling gateway | KEEP (facade) | Bypass if empty tenants | tenant isolation suite |
| pending_clients.json | `engine/authoring_routes.py` | `Folder` (DOMAIN) / `Perimeter` | YES | PRESENT | First-class `clients.json` → then Folder DOMAIN | MIGRATE | Orphan clients | client-zero-programs |
| ProgramSnapshot (mutable SoT) | `engine/program_loader.py`, `program_authoring.py` | `Perimeter` + `ComplianceAssessment` (+ optional Campaign) | YES | ADAPTABLE | Slice B: create via gateway; snapshot = read model | MIGRATE | Demo regression | Michele E2E |
| FrameworkRecord registry | `engine/framework_registry.py` | `Framework` + `LoadedLibrary` | YES | PRESENT | Import YAML libraries; registry becomes cache/index | MIGRATE | Version pin drift | framework import atomic |
| FrameworkVersionRecord | `engine/framework_versions.py` | `LoadedLibrary.version` | PARTIAL | ADAPTABLE | Keep DRAFT/PUBLISH workflow as WayFold until core exposes equivalent UX; pin via LoadedLibrary | KEEP (workflow) / MIGRATE (store) | Published immutability | publish/clone tests |
| FrameworkRequirement | `framework_versions.py` | `RequirementNode` | YES | PRESENT | Sync from library; edit only DRAFT | MIGRATE | Hierarchy loss | CSV atomic + diff |
| CanonicalControl catalog | `engine/control_catalog.py` | `ReferenceControl` | YES | PRESENT | Slice F: catalog reads core | MIGRATE | Code collision | control catalog UI |
| MappingRecord KB | `engine/kb_mappings.py`, `mapping_store.py` | `RequirementMapping` is req↔req only | NO (coverage model) | STRUCTURALLY MISSING | **KEEP** WayFold MappingRecord (FULL/PARTIAL/SUPPORTING + delta + review_status) | KEEP | Semantics drift | draft exclusion, delta isolation |
| Control implementation patch | `engine/control_locking.py` + snapshot | `AppliedControl` | YES | PRESENT | Slice C: write AppliedControl via API; optimistic lock via DB version/ETag | MIGRATE | Lost updates | concurrency 200/409 |
| control_versions.json | `engine/control_locking.py` | DB version / updated_at | YES | PRESENT | Delete after DB CAS | DELETE | False conflicts | concurrency |
| Evidence catalog + binaries | `engine/evidence_storage.py` + snapshot `evidences` | `Evidence`, `EvidenceRevision` | YES | PRESENT | Slice D: single SoT core; binary via attachment | MIGRATE | Dual-store split | binary upload/download |
| RemediationTaskSnapshot | snapshot `tasks` | `TaskNode` / `TaskTemplate` | YES | PRESENT | Slice E: task lifecycle on core | MIGRATE | Orphan tasks | task CRUD |
| Audit JSONL | `engine/audit.py` | CISO activity logs (partial) | PARTIAL | EXTERNAL / ADAPTABLE | Keep append-only application audit; document not tamper-evident | KEEP | Tenant leak | audit scope tests |
| ReportSnapshot | `engine/report_snapshots.py` | (no equivalent product snapshot) | NO | STRUCTURALLY MISSING / EXTERNAL | KEEP report snapshots | KEEP | Stale claims | snapshot immutability |
| RegulatorySource / Snapshot / Change | `engine/regulatory/*` | none | NO | EXTERNAL | KEEP | KEEP | SSRF | regulatory suite |
| FrameworkUpdateSuggestion | `engine/regulatory/*` | none (must not auto-publish) | NO | EXTERNAL | KEEP | KEEP | Silent mutate | suggestion workflow |
| AISuggestion / AI settings | `engine/ai/*` | none | NO | EXTERNAL | KEEP code; feature flag OFF prod | KEEP (disabled) | Silent apply | feature_disabled |
| AutomatedEvidence / connectors | `engine/automated_evidence/*` | Evidence (bridge deferred) | PARTIAL | EXTERNAL | KEEP code; feature flag OFF prod | KEEP (disabled) | False compliance | feature_disabled |
| Portfolio registry JSON | `portfolio_registry.json` | Folder tree + assessments | YES | ADAPTABLE | Derive from core Folders/Perimeters | MIGRATE | Empty portfolio | portfolio filters |
| Unified checklist / readiness / impact | `checklist.py`, `readiness.py`, `impact.py` | composed views | N/A | APPLICATION | Stay WayFold services over gateway data | KEEP | Overstatement | draft mapping + implicit FULL |
| Gap engine | `gap_assessment.py` | none product-grade | N/A | APPLICATION | Rewrite finding semantics (this milestone) | KEEP (fixed) | Delta leakage | gap invariant tests |
| Consultant UX HTML | `ux_pages.py`, `product_pages.py`, `ui_shell.py` | SvelteKit frontend | NO (by decision) | EXTERNAL UX | KEEP WayFold shell (no redesign) | KEEP | — | UI IT tests |
| ciso_bridge ORM export | `ciso_bridge.py` | ORM models | YES | PRESENT | Local/demo only; prod via DRF/gateway | KEEP (bridge) | Prod ORM coupling | bridge optional |

---

## Slice plan (no big bang)

| Slice | Scope | Exit criteria |
|---|---|---|
| **0 (this milestone)** | P0 security, gap semantics, evidence binary SoT, task lifecycle, clients first-class, CSRF/session/MFA/flags, docs | Route tests green; READY FOR REAL CLIENT DATA still NO |
| **A** | Auth/users/RBAC → CISO IAM | Login via core; custom users.json dual-read then deprecate |
| **B** | Client/Program → Folder/Perimeter/Assessment | Zero pending_clients; program metadata on core |
| **C** | Control implementation → AppliedControl + DB CAS | 409 concurrency; delete control_versions.json |
| **D** | Evidence → Evidence/EvidenceRevision | Single SoT; binary round-trip |
| **E** | Tasks → TaskNode | Full lifecycle |
| **F** | Framework/requirements → LoadedLibrary where feasible | Atomic CSV; published immutability retained |
| **G** | Remove obsolete JSON stores | No dual GRC core |

After each slice: unit + integration + E2E + migration validation + deploy SHA check.

---

## CoreGrcGateway (boundary)

Conceptual operations (implemented as `engine/core_gateway.py`; current backend = WayFold stores with CISO bridge hooks):

- `list_clients` / `create_client`
- `list_programs` / `create_program`
- `get_framework_versions` / `get_requirements`
- `get_reference_controls`
- `get_control_implementations` / `update_control_implementation`
- `list_evidence` / `create_evidence`
- `list_tasks` / `create_task` / `update_task`

`UnifiedComplianceService` / HTTP handlers must not call ORM/HTTP details directly.

---

## Documented exceptions (KEEP custom)

1. **MappingRecord coverage model** — CISO `RequirementMapping` is requirement↔requirement; WayFold needs requirement↔canonical with SUPPORTING + `uncovered_delta` + review workflow. **STRUCTURALLY MISSING.**
2. **Regulatory intelligence** — absent in core. **EXTERNAL.**
3. **AI suggestions store** — absent; must stay suggest-only. **EXTERNAL** (flag OFF).
4. **Automated evidence overlay** — bridge to EvidenceRevision deferred. **EXTERNAL** (flag OFF).
5. **ReportSnapshot** — product pin of readiness/gaps at generate-time. **KEEP.**
6. **Application audit JSONL** — until tamper-evidence exists, claim only “append-only application audit log”.

---

## Migration safety

- Backup live demo stores before any cutover.
- Preserve `WF_REVIEW_DEMO_2026`.
- Dual-read verification before destructive replacement.
- No silent drop of Michele/Alfa programs.

## Capability stop-rule

If CISO cannot support a **generic GRC** need, document:

`CAPABILITY | CISO LIMITATION | CODE EVIDENCE | ALTERNATIVES | RECOMMENDATION`

Do **not** invent a second generic GRC core.

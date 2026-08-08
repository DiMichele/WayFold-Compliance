# Gap Report — WayFold Compliance (Phase 0)

Core under evaluation: **CISO Assistant Community** (demo Michele: **PASS**).

Classi: 1 PRESENTE · 2 ADATTABILE · 3 ESTERNA · 4 MANCANTE STRUTTURALMENTE

---

## ALREADY AVAILABLE (class 1)

| Capability | CISO entity / module | Notes |
|---|---|---|
| Frameworks as data | `Framework` + `LoadedLibrary` + YAML | Non hardcoded |
| Requirements + hierarchy | `RequirementNode` | |
| Canonical controls | `ReferenceControl` | ≈ WayFold CanonicalControl |
| Client implementations | `AppliedControl` | ≈ ControlImplementation; reusable across assessments |
| Req↔control mapping | M2M + `RequirementMapping*` | |
| Multi-framework assessment | `ComplianceAssessment` × N | Demo: ISO27001 + NIS2 + NIST CSF |
| Evidence | `Evidence` / `EvidenceRevision` | Demo evidence linked |
| Tasks / remediation | `TaskTemplate`/`TaskNode` + AC status/ETA | |
| Auth / RBAC | `User`, `Role`, `RoleAssignment`, Folder scope | |
| API | DRF + OpenAPI | |
| Import/export libraries | `StoredLibrary.load()` | |
| Dashboard / reporting | Frontend + analytics/export | UI https://localhost:8443 |

---

## AVAILABLE BUT NEEDS ADAPTATION (class 2)

| Capability | Gap | Adaptation |
|---|---|---|
| Client MSP naming | No `Client` model | Use Folder DOMAIN + labels/UX |
| ComplianceProgram | No single multi-FW program entity | Campaign + Perimeter + multiple CA; UX glue |
| FrameworkVersion entity | Library `version` int only | Explicit pin/publish UX + docs |
| Unified checklist | Multi-CA + shared AC works in data | Consultant UX overlay |
| Portfolio dashboard | Per-domain UI exists | Multi-client portfolio view |
| Mapping review states | Mapping exists; WayFold wants DRAFT/AI/HUMAN | Extra workflow fields |
| Owner on controls | Actor/owners present | Confirm UX wiring in consultant flows |
| Snapshots | Partial (`FrameworkSnapshot`) | Program snapshot semantics |

**Naming ≠ gap:** `ReferenceControl`/`AppliedControl`/`Perimeter` are semantic equivalents, not missing capabilities.

---

## MISSING — CUSTOM WAYFOLD (class 3)

| Capability | Why custom |
|---|---|
| Regulatory watcher | Absent in CISO/Probo/Unicis |
| Regulatory diff / hash snapshots | Absent |
| Client-impact engine | Absent |
| Control ROI | Absent |
| Advanced mapping intelligence (+ AI suggest) | Core mapping exists; intelligence layer Wayfold |
| OpenCRE bridge | Specialized component |

---

## UNNECESSARY FOR CURRENT MVP

| Item | Reason |
|---|---|
| Vendor management / full risk engine extras | Out of MVP (§90); already in CISO optionally |
| SAML/SCIM polish | CISO has SSO/SCIM; not required to rebuild |
| Prowler automated evidence | Phase 6 |
| Rewriting auth/evidence/task engines | Covered by core — DO NOT BUILD |
| Unicis as parallel core | Rejected; frameworks-as-code conflicts |

---

## Demo Michele checklist

| Criterion | Result |
|---|---|
| Client Michele Demo (Folder DOMAIN) | PASS |
| Program Cyber Compliance Demo (Perimeter) | PASS |
| Framework A ISO/IEC 27001:2013 (≥2 req) | PASS (200 RA) |
| Framework B NIS2 (≥2 req) | PASS (17 RA) |
| Framework C NIST CSF 2.0 Journey (≥2 req) | PASS (134 RA) |
| Control shared across 2 frameworks | PASS (`CTRL-IAM-DEMO-2`) |
| Control shared across 3 frameworks | PASS (`CTRL-IAM-DEMO-3`) |
| Uncovered / partial requirement | PASS |
| Assessment | PASS |
| Reuse single implementation | PASS |
| Status | PASS |
| Owner | PASS (`AppliedControl.owner` → Actor/admin) |
| Deadline (ETA) | PASS |
| Evidence | PASS |
| Remediation/task | PASS |
| Dashboard/reporting available | PASS (UI 302→app, API health 200) |

**Verdict:** CISO Assistant **rappresenta il concetto WayFold** (una implementazione, più framework). Nessun product blocker di classe 4 sul core domain.

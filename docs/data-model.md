# Data model — WayFold Compliance

## Core (CISO Assistant — reuse, do not duplicate)

| Entity | Role |
|---|---|
| `Folder` (DOMAIN) | Client / tenant boundary |
| `Perimeter` | Compliance program / scope |
| `LoadedLibrary` + `version` | Framework package + pin |
| `Framework` | Loaded framework instance |
| `RequirementNode` | Requirement (hierarchy via parent_urn) |
| `ReferenceControl` | Canonical / common control |
| `AppliedControl` | Client control implementation |
| `ComplianceAssessment` | Assessment bound to one Framework |
| `RequirementAssessment` | Per-requirement assessment row |
| `Evidence` / `EvidenceRevision` | Evidence |
| `TaskTemplate` / `TaskNode` | Remediation tasks |
| `User` / `Role` / `RoleAssignment` | AuthZ scoped by folder |

Semantic aliases (product language only — no DB rename):

- CanonicalControl → ReferenceControl  
- ControlImplementation → AppliedControl  
- Client → Folder DOMAIN  
- ComplianceProgram → Perimeter (+ Campaign optional)

## WayFold Engine overlay (Phase 2)

Stored outside the core DB (JSON snapshots / future engine DB):

| Concept | Fields (conceptual) |
|---|---|
| `MappingRecord` | requirement_id, framework_id/version, canonical_control_ref, relation FULL\|PARTIAL\|SUPPORTING, rationale, uncovered_delta, review_status |
| `ProgramSnapshot` | tenant, program, requirements[], implementations[], mappings[], requirement_implementation_links |
| `UnifiedChecklist` | deduplicated controls + unmapped[] |
| `FrameworkReadinessRow` | FULLY_COVERED / PARTIALLY_COVERED / NOT_COVERED / UNMAPPED / NOT_APPLICABLE counts + implementation_readiness |
| `ControlImpactRow` | readable impact summary (requirements × frameworks × open gaps) |

## WayFold Regulatory store (Phase 4)

Persisted under `engine/data/regulatory/` (not CISO DB):

| Concept | Role |
|---|---|
| `Source` | Configured monitored origin (HTML/JSON/FILE/…) + linked framework/requirement anchors |
| `SourceSnapshot` | Fetched raw + normalized content refs + content/normalized hashes |
| `RegulatoryChange` | Diff inbox (`NEW` → `ACCEPTED`/`IGNORED`) with relevance SUBSTANTIVE/COSMETIC |
| `FrameworkUpdateSuggestion` | Human workflow `CLONE_DRAFT` — no auto-publish |
| `ClientImpactReport` | Projection onto pinned programs via mappings (advisory) |

## WayFold AI store (Phase 5)

Persisted under `engine/data/ai/` (not CISO DB):

| Concept | Role |
|---|---|
| `TenantAISettings` | `ai_processing_enabled` default **false** |
| `AISuggestion` | Mapping / regulatory diff / impact / gap explanation with `AI_SUGGESTED` → human `APPROVED`/`REJECTED` |

AI never publishes frameworks, never auto-approves mappings, never mutates pinned baselines, never marks clients compliant.

## WayFold Automated Evidence store (Phase 6)

Persisted under `engine/data/automated_evidence/` (not CISO DB):

| Concept | Role |
|---|---|
| `ConnectorConfig` | Tenant-scoped scanner connector (`PROWLER_JSON` / fixture); `credential_ref` = env name only |
| `NormalizedFinding` | Provider-agnostic technical check |
| `CheckControlMapping` | check_id → canonical control (default relation **SUPPORTING**) |
| `AutomatedEvidenceRecord` | `EXTERNAL_REFERENCE` evidence suggestion with provenance; `PENDING_REVIEW` → `APPROVED`/`REJECTED`/`STALE` |

Technical PASS never auto-sets AppliedControl IMPLEMENTED or framework readiness.

## Boundaries

- Global KB (libraries, reference controls, published frameworks) ≠ client workspace (applied controls, evidence, tasks).  
- Engine reads core via ORM bridge or API; does not silently mutate published libraries.  
- Tenant isolation enforced in core IAM and re-checked by `engine.authz` before checklist responses.
- Regulatory watcher never silently changes framework data or client baselines.
- AI assistance is optional per tenant and always human-reviewed.
- Automated evidence is SUPPORTING technical signal; human-reviewed; does not replace CISO Evidence engine writes in this phase (engine-side overlay + advisory counts).

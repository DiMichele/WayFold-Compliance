# DATA MIGRATION REPORT — WayFold Compliance

Date: 2026-08-09  
Phase: Slice 0 (security + domain fix) — **no destructive CISO cutover yet**.

## Approach

Per `CORE-REALIGNMENT-PLAN.md`: migrate by slice with dual-read, not big bang.

| Slice | Status | Notes |
|---|---|---|
| 0 Security/domain | DONE (this milestone) | Permissions, gap, mapping semantics, evidence binary SoT, clients first-class |
| A Auth → CISO IAM | NOT STARTED | Custom session hardened interim |
| B Client/Program → Folder/Perimeter | PARTIAL | `clients.json` first-class; ProgramSnapshot still JSON SoT |
| C AppliedControl + DB CAS | NOT STARTED | `control_versions.json` still used |
| D Evidence → EvidenceRevision | PARTIAL | Catalog+binary is single engine SoT; core bridge deferred |
| E TaskNode | PARTIAL | Task lifecycle on snapshot; gateway target TaskNode |
| F Framework libraries | NOT STARTED | WayFold version store kept for DRAFT/PUBLISH UX |
| G Delete obsolete JSON | NOT STARTED | After dual-read validation |

## Current operational stores (interim)

| Store | Path | Role after Slice 0 |
|---|---|---|
| clients.json | `WAYFOLD_DATA_DIR/clients.json` | First-class clients (0..N programs) |
| portfolio_registry.json | data dir | Program index |
| programs/*.json | data dir | Mutable DTO / interim SoT |
| evidence/catalog.json + binaries | data dir | Authoritative evidence |
| kb mappings / frameworks | data dir | WayFold KEEP (structurally missing in core) |
| users.json / assignments | data dir | Interim until Slice A |
| audit/events.jsonl | data dir | Append-only application log |
| pending_clients.json | legacy | Migrated into clients.json on read |

## Safety

- No live demo wipe in this milestone.
- Preserve `WF_REVIEW_DEMO_2026`.
- Before Slice A–G cutover: backup `data/engine` + `data/db`, dual-read verification, rollback plan.

## Rollback

Redeploy previous SHA; restore `data/engine` tarball. Gateway allows swapping backend without UI rewrite once CISO adapters land.

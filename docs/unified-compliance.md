# Unified Compliance — WayFold Phase 2

## Goal

Produce a **single checklist** for a client program spanning multiple pinned framework versions, reusing one implementation per canonical control, while preserving framework-specific deltas and never hiding unmapped requirements.

## Reuse map

| WayFold concept | CISO / store |
|---|---|
| CanonicalControl | `ReferenceControl` (+ WayFold `canonical_control_ref`) |
| ControlImplementation | `AppliedControl` |
| Requirement | `RequirementNode` / `RequirementAssessment` |
| Client / Program | `Folder` DOMAIN / `Perimeter` |
| FrameworkVersion pin | `LoadedLibrary.version` on assessment framework |
| Req↔Control mapping FULL/PARTIAL/SUPPORTING | WayFold overlay (`MappingRecord`) — CISO has req↔req `RequirementMapping` FULL/PARTIAL only |

## Engine layout

```text
apps/wayfold-compliance/engine/
  domain.py          domain dataclasses
  checklist.py       unified checklist builder (§34)
  readiness.py       framework readiness
  impact.py          readable control impact / ROI
  authz.py           tenant isolation gate
  mapping_store.py   JSON mapping persistence helpers
  program_loader.py  load ProgramSnapshot
  ciso_bridge.py     export snapshot from live CISO ORM
  cli.py             text/JSON CLI
  api.py             local HTML + JSON HTTP surface (:8092)
  fixtures/          Michele Phase 2 demo program
  tests/             unit tests (no Docker required)
```

## Algorithm

1. Take pinned framework versions already bound to program assessments  
2. Collect assessable leaf requirements  
3. Load APPROVED (non-REJECTED) mappings  
4. Resolve canonical controls  
5. Deduplicate by `canonical_control_ref`  
6. Preserve `uncovered_delta` per framework row  
7. Emit UNMAPPED requirements explicitly  
8. Attach client `AppliedControl` status/owner/deadline/evidence/tasks when present  

## Mapping relations

- `FULL` — control fully addresses requirement when implemented  
- `PARTIAL` — implemented control still leaves `uncovered_delta` → readiness stays `PARTIALLY_COVERED`  
- `SUPPORTING` — helpful but not sufficient → at most `PARTIALLY_COVERED`  

## Commands

```powershell
cd apps/wayfold-compliance
python -m engine.tests.test_unified_compliance
python -m engine --superuser --format text
# oppure: python -m engine --actor-tenants=tenant-michele --format text
python -m engine.api
# browser (auth esplicita obbligatoria): http://127.0.0.1:8092/checklist?superuser=1
# oppure: .../checklist?actor_tenants=tenant-michele
```

Live CISO export (backend container, engine mounted):

```text
PYTHONPATH=/code:/path/to/wayfold-compliance \
  python engine/ciso_bridge.py --seed-phase2-mappings --out .../michele_from_ciso.json
```

## Demo Michele (fixture)

- 3 frameworks, shared `CTRL-IAM-001` across all three  
- PARTIAL mappings with explicit deltas  
- SUPPORTING mapping on recovery  
- ≥2 UNMAPPED requirements  
- Mixed IMPLEMENTED / IN_PROGRESS / NOT_IMPLEMENTED  

## Out of scope (later phases)

AI mapping suggestions, regulatory watcher, portfolio UX polish (Phase 3), Prowler.

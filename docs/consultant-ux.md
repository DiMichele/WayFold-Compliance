# Consultant UX — WayFold Phase 3

## Goal

Daily consultant workflow over the CISO core + Phase 2 Unified Compliance engine: portfolio → client → gaps → owners/deadlines/evidence/tasks → report. No Regulatory Watcher, no AI.

## Surfaces

| View | Route (HTML) | JSON |
|---|---|---|
| Portfolio | `/portfolio` | `/api/portfolio` |
| Client dashboard | `/client?program_id=…` | `/api/client` |
| Gap assessment | `/gaps` (+ filters incl. deadline range) | `/api/gaps` |
| Control detail | `/control?control_ref=…` | `/api/control` |
| Owner view | `/owners` | `/api/owners` |
| Deadline view | `/deadlines` | `/api/deadlines` |
| Evidence | `/evidence` | `/api/evidence` |
| Tasks | `/tasks` | `/api/tasks` |
| Report | `/report` | `/report.csv` |
| Unified checklist | `/checklist` | `/api/unified-checklist` |

Auth (required): `?superuser=1` **or** `?actor_tenants=<tenant-id>[,…]`.

## Modules

```text
engine/portfolio.py          portfolio + client dashboard
engine/gap_assessment.py     gap rows + filters
engine/consultant_views.py   owner / deadline / evidence / task
engine/reports.py            HTML print-friendly + CSV
engine/ux_pages.py           dense HTML shells
engine/api.py                HTTP :8092
engine/fixtures/portfolio_registry.json
engine/fixtures/alfa_phase3_program.json
```

## Reuse

- Controls / evidence / tasks / owners / deadlines come from program snapshots exported from CISO (`AppliedControl`, Evidence counts, Task counts).
- Checklist / readiness / impact reused from Phase 2 services — no second mapping engine.
- Tenant isolation via `engine.authz` before every response.

## Commands

```powershell
cd apps/wayfold-compliance
python -m engine.tests.test_unified_compliance
python -m engine.tests.test_consultant_ux
python -m engine.api
# http://127.0.0.1:8092/portfolio?superuser=1
```

## Out of scope

Regulatory watcher, AI mapping, Prowler, production deploy/DNS.

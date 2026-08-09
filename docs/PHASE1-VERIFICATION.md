# PHASE 1 VERIFICATION — WayFold Compliance

## Verdict

**PASS**

## Commit verified

`bb5e86455648817dc74bb5b5e8a77a3a4bcb405a` (`bb5e864 chore(compliance): start overnight automation`)

Core runtime: CISO Assistant Community **v3.20.8** (container `backend`, Strategy B).

## Acceptance matrix

| Criterion | Result | Evidence |
|---|---|---|
| Client / tenant (Folder DOMAIN) | PASS | `Michele Demo` Folder content_type=DOMAIN |
| Program / perimeter | PASS | `Cyber Compliance Demo` Perimeter `WF-DEMO-PROG` |
| Framework / requirements as data | PASS | ISO27001:2013, NIS2, NIST CSF 2.0 Journey loaded from libraries (not hardcoded) |
| ReferenceControl / AppliedControl | PASS | 342 ReferenceControls in KB; demo AppliedControls `CTRL-IAM-DEMO-2/3` |
| Assessment | PASS | 3 ComplianceAssessments (200 / 17 / 134 requirement assessments) |
| Evidence | PASS | `WF-EVID MFA Policy Screenshot` linked to `CTRL-IAM-DEMO-3` |
| Task / remediation | PASS | TaskTemplate + TaskNode pending for uncovered Framework A req |
| Owner / deadline | PASS | Owner Actor on DEMO-3; ETA on both AppliedControls |
| RBAC + tenant isolation server-side | PASS | Live isolation check: Michele-scoped viewer cannot see Alfa folder/control/evidence; API unauthenticated → 401 |
| Demo Michele riproducibile | PASS | `docs/michele_demo_seed.py` idempotent replay → `ACCEPTANCE: PASS` |
| Migrations / bootstrap | PASS | `manage.py showmigrations` all applied on running DB |
| Docker startup | PASS | `backend` healthy; `frontend`/`caddy`/`huey` up; UI `https://localhost:8443` → 302; `/api/health/` → `{"status":"ok"}` |
| Framework version pin | PASS | Assessments bound to Framework backed by `LoadedLibrary.version` (e.g. nis2 v3, nist-csf v2) |
| Optimistic locking | N/A (non-blocking) | Core `AppliedControl` has `updated_at`, no integer `version` field — defer until core/extension supports it |
| Production build (pertinent) | PASS | Prebuilt compose images running; frontend container serves app |

## Tests

| Suite | Result | Notes |
|---|---|---|
| Michele demo seed acceptance | PASS | Replayed with `PYTHONPATH=/code` |
| Tenant isolation (live ORM) | PASS | Viewer on Michele cannot leak Alfa control/evidence/folder; cannot `change_appliedcontrol` on Alfa |
| CISO `pytest` in runtime image | SKIP / WARN | `pytest` not installed in production backend image — source tests exist under `vendor/.../backend/iam/tests/` |
| Automation unit tests | Not re-run this gate | Orthogonal to Working Core |

## Build / runtime

- Docker Compose core: **PASS** (healthy backend)
- API health: **PASS**
- Protected API (`/api/frameworks/`, `/api/stored-libraries/`): **401** without auth — **PASS**

## Security

- Folder-scoped `RoleAssignment.get_accessible_object_ids` / `is_access_allowed` enforced in core views
- Cross-tenant evidence/control leak check: **PASS**
- No WayFold custom auth bypass introduced (none built — reuse CISO IAM)

## Demo Michele replay

Workflow verified via seed + DB inspection:

`Michele Demo → Cyber Compliance Demo → 3 frameworks → shared AppliedControls → status/owner/ETA → evidence → task → assessments`

| Check | Result |
|---|---|
| Shared control across 2 frameworks | PASS (`CTRL-IAM-DEMO-2`) |
| Shared control across 3 frameworks | PASS (`CTRL-IAM-DEMO-3`) |
| Partial / uncovered requirement | PASS |
| Mixed statuses | PASS |

## Failures / fixes

None in this verification run. `fixAttemptsUsed: 0`.

## Warnings (non-blocking)

1. `Perimeter.overall_compliance()` related_name mismatch in upstream — seed skips; not required for Phase 1 Working Core.
2. Runtime image lacks `pytest`; isolation verified live instead of upstream unit suite.
3. Local stack uses SQLite + `DEBUG=True` (dev compose) — expected for LOCAL_OVERNIGHT, not production hardening.
4. Thin consultant UX / compose wrapper under `apps/wayfold-compliance` deferred to Phase 2–3 (Phase 1 = Working Core reuse).
5. `docs/data-model.md` was absent at verify time — to be added with Phase 2.

## Final verdict

**PASS** — Phase 1 Working Core (CISO Assistant + Strategy B) meets blocking acceptance criteria. Orchestrator may tag `phase-1-complete` after this report.

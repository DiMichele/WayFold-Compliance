# ROUTE PERMISSION MATRIX — WayFold Compliance

Date: 2026-08-09  
Rule: zero state-changing routes without explicit permission. GET must not mutate.

Legend: PUBLIC = no auth · TENANT = server-side tenant gate · MUT = state-changing

| METHOD | PATH | PUBLIC? | PERMISSION | TENANT SCOPED? | MUT? | TEST ID |
|---|---|---|---|---|---|---|
| GET | `/login` | YES | — | NO | NO | SEC-AUTH-01 |
| POST | `/login` | YES | — (rate limited) | NO | YES (session) | SEC-AUTH-02 |
| GET | `/logout` | YES | — | NO | YES (revoke) | SEC-SESSION-01 |
| GET | `/healthz` | YES | — | NO | NO | — |
| GET | `/api/health` | YES | — | NO | NO | — |
| GET | `/api/build-info` | NO | authenticated | NO | NO | SEC-BUILD-01 |
| GET | `/portfolio` | NO | auth | YES | NO | — |
| GET | `/api/portfolio` | NO | auth | YES | NO | — |
| GET | `/clients` | NO | auth | YES | NO | — |
| GET | `/clients/new` | NO | `client.create` | NO | NO | SEC-CLIENT-01 |
| POST | `/clients/new` | NO | `client.create` | NO | YES | SEC-CLIENT-02 |
| GET | `/programs/new` | NO | `program.create` | YES (assigned) | NO | SEC-PROG-01 |
| POST | `/programs/new` | NO | `program.create` | YES (form tenant) | YES | SEC-PROG-02 |
| GET | `/control/edit` | NO | `control.write` | YES (program) | NO | SEC-CTRL-UI-01 |
| POST | `/api/control/update` | NO | `control.write` | YES (program) | YES | SEC-CTRL-01 |
| GET | `/evidence/new` | NO | `evidence.write` | YES (program) | NO | SEC-EV-01 |
| POST | `/evidence/new` | NO | `evidence.write` | YES (program) | YES | SEC-EV-02 |
| GET | `/api/evidence/{id}/download` | NO | `evidence.download` | YES | NO | SEC-EV-03 |
| GET | `/tasks/new` | NO | `task.write` | YES | NO | SEC-TASK-01 |
| POST | `/tasks/new` | NO | `task.write` | YES | YES | SEC-TASK-02 |
| GET | `/tasks/edit` | NO | `task.write` | YES | NO | SEC-TASK-03 |
| POST | `/tasks/edit` | NO | `task.write` | YES | YES | SEC-TASK-04 |
| GET | `/settings` | NO | auth (users list gated) | NO | NO | SEC-SET-01 |
| GET | `/api/settings` | NO | `user.admin` | NO | NO | SEC-SET-02 |
| GET | `/audit` | NO | `audit.read` | YES (server filter) | NO | SEC-AUD-01 |
| GET | `/api/audit` | NO | `audit.read` | YES (server filter) | NO | SEC-AUD-02 |
| GET | `/frameworks` | NO | auth / `kb.read` | NO | NO | — |
| POST | `/frameworks/new` | NO | `kb.write` | NO | YES | — |
| POST | `/frameworks/publish` | NO | `framework.publish` | NO | YES | — |
| POST | `/api/frameworks/clone` | NO | `kb.write` | NO | YES | SEC-GET-01 |
| POST | `/api/frameworks/publish` | NO | `framework.publish` | NO | YES | SEC-GET-01 |
| GET | `/api/frameworks/clone` | NO | — | — | — | **405** SEC-GET-01 |
| GET | `/api/frameworks/publish` | NO | — | — | — | **405** SEC-GET-01 |
| GET | `/api/frameworks/patch` | NO | — | — | — | **405/deleted** SEC-GET-01 |
| GET | `/mappings` | NO | auth | optional | NO | — |
| POST | `/mappings/new` | NO | `mapping.write` | NO | YES | — |
| GET | `/api/regulatory/check` | NO | — | — | — | **405** SEC-GET-01 |
| GET | `/api/regulatory/review` | NO | — | — | — | **405** SEC-GET-01 |
| GET | `/api/auto-evidence/ingest` | NO | feature flag | — | — | **404/405** |
| GET | `/api/auto-evidence/review` | NO | feature flag | — | — | **404/405** |
| GET | `/api/ai/*` (mutating) | NO | feature flag OFF default | — | — | **404** feature_disabled |
| GET | `/ai/*` | NO | feature flag OFF default | — | — | **404** |
| GET | `/connectors` | NO | feature flag OFF default | — | — | **404** |

## Role → permission highlights

| Role | control.write | evidence.write | task.write | client.create | program.create | user.admin |
|---|---|---|---|---|---|---|
| SUPER_ADMIN | YES | YES | YES | YES | YES | YES |
| CONSULTANT | YES | YES | YES | YES | YES (assigned) | NO |
| CLIENT_ADMIN | YES | YES | YES | NO | NO | NO |
| CLIENT_MEMBER | YES | YES | YES | NO | NO | NO |
| VIEWER | NO | NO | NO | NO | NO | NO |

## CSRF

All browser cookie-session mutations require double-submit CSRF + same-origin Origin/Referer check (unless `WAYFOLD_CSRF_DISABLE` / test opt-out).

Tests: SEC-CSRF-01 (missing / bad origin / valid).

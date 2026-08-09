# SECURITY REMEDIATION REPORT — WayFold Compliance

Date: 2026-08-09  
Scope: Architecture reconciliation milestone — P0 endpoint auth, CSRF, session, MFA, filesystem, feature flags.

## Status summary

| Item | Result | Evidence |
|---|---|---|
| Control write permission | PASS | `SEC-CTRL-01` VIEWER → 403 |
| Evidence create authz | PASS | `PERM_EVIDENCE_WRITE` + tenant on GET/POST `/evidence/new` |
| Task create/edit authz | PASS | `PERM_TASK_WRITE` + tenant; `/tasks/edit` implemented |
| Settings disclosure | PASS | `/api/settings` requires `user.admin`; CLIENT_* → 403 (`SEC-SET-01`) |
| Audit tenant scope | PASS | Server filters by actor tenants; QS `tenant_id` cannot expand scope |
| State-changing GET | PASS | clone/publish/patch/regulatory/auto-evidence → 405 (`SEC-GET-01`) |
| CSRF | PASS | double-submit + Origin check (`SEC-CSRF-01`) |
| Filesystem permissions | PASS (deploy) | removed `chmod a+rwX`; chown container UID; secrets 600 |
| Regulatory file scheme | PASS | `file://` / `fixture://` denied outside TEST MODE |
| Login rate limit | PASS | IP+username backoff (`login_throttle.py`) |
| Session revocation | PASS | logout + bump on role/tenant/password change hooks |
| MFA enforcement | PARTIAL | Privileged roles without enroll denied in prod (`WAYFOLD_MFA_ENFORCE=1`); temp review credential bypass remains |
| Feature flags server-side | PASS | AI/connectors/auto-evidence → 404 `feature_disabled` when OFF |
| Malware scan | NOT IMPLEMENTED | `scan_content` returns `NOT_IMPLEMENTED` (not PASS) |

## Temporary review credential

Still present via env (`WAYFOLD_AUTH_USER` / `WAYFOLD_AUTH_PASSWORD`). Marked TEMPORARY REVIEW CREDENTIAL. Blocks READY FOR REAL CLIENT DATA.

## Documentation truth corrections

- MFA: PARTIAL (enforcement for privileged roles without enroll; enrollment UX still incomplete)
- Malware scan: NOT IMPLEMENTED (hook only)
- Audit: application append-only JSONL — **not** immutable/tamper-evident trail
- Backup: see BACKUPS / DATA-MIGRATION — scheduled off-host still required for REAL CLIENT DATA

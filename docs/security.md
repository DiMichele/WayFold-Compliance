# Security — WayFold Compliance

## Authentication

- Cookie session firmata HMAC-SHA256 (`wf_session`)
- `HttpOnly` + `SameSite=Lax` + `Secure` (quando `X-Forwarded-Proto=https`)
- Idle timeout: 45 minuti (sliding)
- Absolute timeout: 8 ore
- Production: refuse start if `WAYFOLD_SESSION_SECRET` missing (`WAYFOLD_ENV=production` or locked-down open access)
- No known-dev secret fallback in production
- Logout revokes token server-side; password/role/tenant assignment bumps invalidate sessions
- Login rate limit: IP + username with backoff (passwords never logged)
- Route pubbliche: `/login`, `/logout`, `/healthz`, `/api/health`
- Produzione: `WAYFOLD_OPEN_ACCESS=0`, `WAYFOLD_ALLOW_QS_AUTH=0`

## CSRF

Browser mutations with session cookie require double-submit CSRF (`wf_csrf` + form/header) and same-origin Origin/Referer enforcement.

## Temporary review credential

```text
TEMPORARY REVIEW CREDENTIAL
```

Configurata via env (`WAYFOLD_AUTH_USER` / `WAYFOLD_AUTH_PASSWORD`), non in repository.
Ruolo effettivo: `SUPER_ADMIN`. Non accettabile per dati cliente reali.

## RBAC

Ruoli engine: `SUPER_ADMIN`, `CONSULTANT`, `CLIENT_ADMIN`, `CLIENT_MEMBER`, `VIEWER`.

- `SUPER_ADMIN`: bypass tenant
- `CONSULTANT`: solo tenant assegnati (`consultant_assignments.json`); `client.create` / `program.create` solo su tenant assegnati
- Ruoli client: solo `tenant_ids` membership
- VIEWER: no `control.write` / `evidence.write` / `task.write`
- `/api/settings` user directory: `user.admin` only

Vedi `ROUTE-PERMISSION-MATRIX.md`.

## Evidence

- Storage privato sotto `WAYFOLD_DATA_DIR/evidence/`
- Download solo via `/api/evidence/{id}/download` con authz tenant+ruolo
- Upload: multipart binario reale; MIME + extension + magic where applicable
- `application/octet-stream` alone ≠ valid
- Malware scan hook: **NOT IMPLEMENTED** (must not be claimed PASS)

## Framework immutability

`PUBLISHED` FrameworkVersion non modificabile in-place. Workflow: clone draft → edit → publish.  
Probe GET `/api/frameworks/patch` removed (405).

## Audit

Append-only JSONL in `WAYFOLD_DATA_DIR/audit/events.jsonl`.  
Classification: **application append-only audit log** — not a tamper-evident immutable trail.  
Tenant filter enforced server-side (never trust `?tenant_id=` alone).

## MFA

TOTP puro Python (`engine/mfa.py`).  
Privileged roles (`SUPER_ADMIN` / `CONSULTANT`) without enrollment cannot receive production session when `WAYFOLD_MFA_ENFORCE=1`.  
Temporary review credential may bypass.  
**Classification:** MFA = PARTIAL (enforcement path present; full enroll UX incomplete).

## Feature flags (server-side)

Default OFF in production:

- `WAYFOLD_FEATURE_AI`
- `WAYFOLD_FEATURE_FW_SUGGESTIONS`
- `WAYFOLD_FEATURE_CONNECTORS`
- `WAYFOLD_FEATURE_AUTO_EVIDENCE`

Hidden UI is insufficient — routes return 404 `feature_disabled`.

## SSRF (Regulatory Watcher)

Production fetch: HTTP/HTTPS only.  
`file://` and `fixture://` denied unless `WAYFOLD_TEST_MODE=1`.  
Blocks localhost, loopback, RFC1918, link-local, metadata, `gopher://`.

## Headers

Engine + nginx: HSTS, CSP, XCTO, Referrer-Policy, Permissions-Policy, frame-ancestors / X-Frame-Options.

## Deploy filesystem

No world-writable `data/engine` / `data/db`.  
Ownership via container UID/GID; secrets `600`; directories `750`.  
Deploy aborts if world-writable paths remain.

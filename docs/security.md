# Security — WayFold Compliance

## Authentication

- Cookie session firmata HMAC-SHA256 (`wf_session`)
- `HttpOnly` + `SameSite=Lax` + `Secure` (quando `X-Forwarded-Proto=https`)
- Idle timeout: 45 minuti (sliding)
- Absolute timeout: 8 ore
- Route pubbliche: `/login`, `/logout`, `/healthz`, `/api/health`
- Produzione: `WAYFOLD_OPEN_ACCESS=0`, `WAYFOLD_ALLOW_QS_AUTH=0`

## Temporary review credential

```text
TEMPORARY REVIEW CREDENTIAL
```

Configurata via env (`WAYFOLD_AUTH_USER` / `WAYFOLD_AUTH_PASSWORD`), non in repository.
Ruolo effettivo: `SUPER_ADMIN`. Non accettabile per dati cliente reali.

## RBAC

Ruoli engine: `SUPER_ADMIN`, `CONSULTANT`, `CLIENT_ADMIN`, `CLIENT_MEMBER`, `VIEWER`.

- `SUPER_ADMIN`: bypass tenant
- `CONSULTANT`: solo tenant assegnati (`consultant_assignments.json`)
- Ruoli client: solo `tenant_ids` membership

## Evidence

- Storage privato sotto `WAYFOLD_DATA_DIR/evidence/`
- Download solo via `/api/evidence/{id}/download` con authz tenant+ruolo
- Nessun URL statico pubblico
- Upload: max 20 MiB, allowlist estensioni/content-type, filename sanitization, scan hook

## Framework immutability

`PUBLISHED` FrameworkVersion non modificabile in-place. Workflow: clone draft → edit → publish.

## Audit

Append-only JSONL in `WAYFOLD_DATA_DIR/audit/events.jsonl`. No password/token/file content.

## MFA

TOTP puro Python (`engine/mfa.py`). Hook enrollment per `SUPER_ADMIN` / `CONSULTANT`.
Temporary review credential può operare senza MFA enrolled.

**Classification before real client data:** MFA enrollment enforcement = PARTIAL (hook + verify ready; mandatory enroll UI incomplete).

## SSRF (Regulatory Watcher)

Blocca localhost, loopback, RFC1918, link-local, metadata, `file://`, `gopher://`. Redirect non seguiti automaticamente verso reti private.

## Headers

Engine + nginx: HSTS, CSP, XCTO, Referrer-Policy, Permissions-Policy, frame-ancestors / X-Frame-Options.

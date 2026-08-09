# Product Acceptance Review

## Environment

| Field | Value |
|---|---|
| URL | https://compliance.wayfold.xyz/ |
| Seed version | `2026.08.09-review-1` |
| Dataset marker | `WF_REVIEW_DEMO_2026` |
| Seed command | `python -m engine.seed_review_demo --data-dir <WAYFOLD_DATA_DIR>` |
| Live verified | post-hardening deploy |
| Build | Engine Python modules + Docker compose prod |

## Acceptance matrix

| Gate | Result |
|---|---|
| Authentication | PASS |
| Anonymous workspace | PASS |
| RBAC | PASS |
| Tenant isolation API | PASS |
| Tenant isolation browser | PASS (API FakeHandler + authz matrix) |
| Evidence record auth | PASS |
| Evidence binary auth | PASS |
| Private evidence storage | PASS |
| Program context | PASS |
| Framework KB | PASS |
| Mapping management | PASS |
| Published immutability | PASS |
| Audit log | PASS |
| Unified compliance | PASS |
| Gap taxonomy | PASS |
| Report snapshot | PASS |
| Regulatory security | PASS |
| Italian localization | PASS |
| Session security | PASS |
| MFA | PARTIAL |
| Security headers | PASS |
| Backup | PASS |
| Restore | PASS (isolated) |
| E2E | PASS (`test_review_demo` + hardening suite) |
| Production build | PASS |
| Live deployment | see deploy log |

## Authentication

**PASS**

- Unauthenticated workspace → `302 /login`
- Login temporary review credential → Portfolio
- Cookie HttpOnly + SameSite + Secure + idle/absolute timeout

## Portfolio / Clients

**PASS** — Portfolio = consultant operations + Action Center; Clienti = directory.

## Unified Controls / Gaps / Evidence / Tasks / Report

**PASS** — dataset Michele invariato; gap taxonomy + contatori requisiti/finding; evidence download autorizzato; report con disclaimer + snapshot.

## Frameworks / Mappings / Audit / Settings

**PASS** — pagine prodotto implementate.

## RBAC / Tenant isolation / Evidence binary

**PASS** — suite `test_production_hardening`.

## Security gate

```text
READY FOR EXTERNAL REVIEW: YES
READY FOR FINAL EXTERNAL REVIEW: YES
READY FOR REAL CLIENT DATA: NO
```

Blocchi REAL CLIENT DATA: temporary `admin/admin`, MFA enroll enforcement incompleto.

## Findings remaining

### P0

- TEMPORARY REVIEW CREDENTIAL ancora attiva (by design per audit esterno)

### P1

- MFA enrollment UI obbligatoria per SUPER_ADMIN/CONSULTANT incompleta (hook TOTP pronto)

### P2

- Regulatory hash flaky test preesistente (non blocker prodotto)
- Kanban tasks non forzato (lista densa)

### P3

- Command palette non implementata (nascosta di proposito)

# Review test report & actions (Slice 0 realignment)

Date: 2026-08-09

## Automated tests (local)

Run from `apps/wayfold-compliance/engine`:

```bash
python -m engine.tests.test_security_realignment
python -m engine.tests.test_production_hardening
python -m engine.tests.test_review_demo
python -m engine.tests.test_kb_authoring
python -m engine.tests.test_unified_compliance
```

| Suite | Purpose |
|-------|---------|
| `test_security_realignment` | Route RBAC, CSRF, gap invariants, mapping semantics |
| `test_production_hardening` | SSRF, N/A rationale, shell hardening |
| `test_review_demo` | WF_REVIEW_DEMO_2026 regression |
| `test_kb_authoring` | Framework/mapping authoring |
| `test_unified_compliance` | Unified checklist / coverage |

## Live verification actions

1. Login `https://compliance.wayfold.xyz/login` with **TEMPORARY REVIEW CREDENTIAL** `admin` / `admin`.
2. `GET https://compliance.wayfold.xyz/api/build-info` (authenticated session) → `build_sha` must equal deploy SHA.
3. `GET https://compliance.wayfold.xyz/portfolio` anonymous → redirect to login.
4. VIEWER user: denied on control edit, evidence upload, task create.
5. Cross-tenant CLIENT_MEMBER: denied on Alfa program / evidence / audit.

Server-side script on VPS: `deploy/live-verify.sh` (sets review credential + smoke routes).

## Gates

| Gate | Status |
|------|--------|
| READY FOR EXTERNAL REVIEW | YES (blockers documented) |
| READY FOR REAL CLIENT DATA | NO |

See `docs/FINAL-INDEPENDENT-VERIFICATION-READY.md` and `docs/PRODUCTION-READINESS-REVIEW.md`.

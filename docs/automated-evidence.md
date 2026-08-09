# Automated Evidence — WayFold Phase 6

## Goal

Ingest technical scanner results (Prowler-compatible JSON) as **SUPPORTING** evidence signals. Humans review. Technical PASS never marks a control/requirement/framework compliant.

## Architecture

```text
ConnectorConfig (tenant-scoped)
      │
      ▼
ScannerAdapter (ProwlerJsonAdapter)
      │
      ▼
NormalizedFinding
      │
      ▼
check → canonical control mapping (SUPPORTING)
      │
      ▼
AutomatedEvidenceRecord (PENDING_REVIEW → APPROVED|REJECTED)
      │
      ▼
Advisory counts only (no AppliedControl status mutation)
```

Store: `engine/data/automated_evidence/` (outside CISO DB).  
Semantic evidence type: `EXTERNAL_REFERENCE` with provenance (adapter, check_id, severity, region).

## Environment note

Live Prowler clone/run on Windows remains an **ENVIRONMENT BLOCKER** (path length). Phase 6 ships a fixture-compatible Prowler JSON adapter; replace `source_uri` with a real export path when available. Credentials only via `credential_ref` (env var name), never inline.

## API (:8092)

| Path | Role |
|---|---|
| `/connectors` | HTML connector list |
| `/auto-evidence` | HTML evidence inbox |
| `/api/auto-evidence/connectors` | JSON connectors |
| `/api/auto-evidence` | JSON evidence |
| `/api/auto-evidence/ingest?connector_id=` | Ingest (idempotent) |
| `/api/auto-evidence/review?evidence_id=&status=` | Human approve/reject |
| `/api/auto-evidence/counts` | Advisory approved counts by control |

Auth: `superuser=1` or `actor_tenants=…` (fail-closed).

## Demo

```powershell
python -c "from engine.automated_evidence.demo import run_demo_ingest; print(run_demo_ingest())"
```

Fixture: `engine/fixtures/automated_evidence/prowler-aws-sample.json`.

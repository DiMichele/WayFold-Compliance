# Demo Review Dataset — WF_REVIEW_DEMO_2026

Dataset deterministico per revisione prodotto esterna su `https://compliance.wayfold.xyz/`.

## Marker

```text
WF_REVIEW_DEMO_2026
```

Seed version: `2026.08.09-review-1`

## Seed command

```powershell
cd apps/wayfold-compliance
python -m engine.seed_review_demo --write-fixtures
# produzione / data dir esplicita:
python -m engine.seed_review_demo --data-dir <WAYFOLD_DATA_DIR>
```

In deploy VPS lo script `deploy/update-remote.sh` esegue automaticamente:

```bash
docker exec wayfold-compliance-engine \
  python -m engine.seed_review_demo --data-dir /var/lib/wayfold-compliance
```

Il reset è **safe**: elimina/riscrive solo record con marker demo / `[Demo]`. Non fa DROP/TRUNCATE del DB GRC.

## Clients (5)

| Client | Tenant ID | Program | Frameworks |
|---|---|---|---|
| Michele S.r.l. [Demo] | `tenant-michele-demo` | Cyber Compliance 2026 | ISO/IEC 27001@2022, NIS2 Italia@2026.1, PSNC@2025.3 |
| Alfa Cloud S.p.A. [Demo] | `tenant-alfa-demo` | Cloud Qualification 2026 | QC4@2025.1, ISO/IEC 27001@2022 |
| Beta Finance S.p.A. [Demo] | `tenant-beta-demo` | ICT Resilience 2026 | DORA@2025.1, NIS2 Italia@2026.1 |
| Nova Health S.r.l. [Demo] | `tenant-nova-demo` | AI Governance & Security 2026 | AI Act@2026.1, ISO/IEC 42001@2023, NIS2@2026.1 |
| Delta Services S.p.A. [Demo] | `tenant-delta-demo` | Cloud Security Assurance 2026 | CSA STAR/CCM@4.0, ISO/IEC 27001@2022 |

## Michele — programma ricco

- Scope: Corporate IT + servizi critici
- Status: ACTIVE
- Framework pinned (non `latest`)
- NIS2 2026.2 DRAFT disponibile ma **non** assegnata (banner nuova versione)

### Unified controls (8)

| Ref | Status | Owner | Due |
|---|---|---|---|
| CTRL-IAM-001 | IN_PROGRESS | Luca Rinaldi | 2026-08-07 (overdue) |
| CTRL-IR-001 | IMPLEMENTED | Sara Moretti | — |
| CTRL-SUP-001 | NOT_IMPLEMENTED | Sara Bianchi | 2026-08-18 |
| CTRL-BCP-001 | IMPLEMENTED | Marco Conti | — |
| CTRL-LOG-001 | IN_PROGRESS | Luca Rinaldi | 2026-08-25 |
| CTRL-GOV-001 | IMPLEMENTED | Michele Ferri | — |
| CTRL-VULN-001 | NOT_APPLICABLE | Luca Rinaldi | — (+ motivazione) |
| CTRL-ENC-001 | NOT_IMPLEMENTED | Luca Rinaldi | 2026-09-15 |

### Mapping critico IAM

```text
ISO-A.5.15 → CTRL-IAM-001 FULL
ISO-A.5.18 → CTRL-IAM-001 FULL
NIS2-01    → CTRL-IAM-001 FULL
PSNC-01    → CTRL-IAM-001 PARTIAL
  delta: revisione trimestrale accessi privilegiati asset critici
```

`CTRL-IAM-001` compare **una sola volta** nella checklist unificata.

### Unmapped

`PSNC-06` resta volontariamente UNMAPPED.

### Evidence (8) + reuse

- EV-001 Access Control Policy v4 → CTRL-IAM-001 + CTRL-GOV-001 (shared)
- EV-004 Incident Response Plan → CTRL-IR-001 + CTRL-BCP-001 (shared)
- Stati: VALID / EXPIRING / PARTIAL / REVIEW_REQUIRED

### Tasks (8)

TASK-001…TASK-008 con TODO / IN_PROGRESS / REVIEW / DONE; TASK-001 overdue.

### Gaps attesi

- Implementation: CTRL-SUP-001 NOT_IMPLEMENTED
- Partial: PSNC-01 → IAM PARTIAL
- Unmapped: PSNC-06
- Evidence gap: Q2 Privileged Access Review PARTIAL
- Overdue remediation: TASK-001

## Storage model

I dati demo sono `ProgramSnapshot` JSON nel volume engine (`WAYFOLD_DATA_DIR`), caricati dal normale application layer (`portfolio_registry.json` → loader → checklist/readiness/gaps/UI).

**Non** sono hardcoded nel frontend.

## Fixture versionate

```text
engine/fixtures/review/
  michele_cyber_2026.json
  alfa_cloud_2026.json
  beta_finance_2026.json
  nova_health_2026.json
  delta_services_2026.json
  portfolio_registry.json
```

I test unitari Phase 2/3 continuano a usare `michele_phase2_program.json` / `alfa_phase3_program.json` separati.

# WayFold Compliance

Applicativo privato GRC multi-framework per consulenza cybersecurity.

- Dominio previsto: `compliance.wayfold.xyz`
- Stato: **Phase 0 COMPLETE** (core selezionato, demo Michele PASS) · **Phase 1** soggetta a verifica overnight
- Raccomandazione: [`docs/PHASE0-RECOMMENDATION.md`](docs/PHASE0-RECOMMENDATION.md)
- Progress: [`docs/PROGRESS.md`](docs/PROGRESS.md)
- Overnight automation: [`automation/INSTALL-AUTOMATION.md`](automation/INSTALL-AUTOMATION.md)

## Decisione Phase 0

- **Core:** CISO Assistant Community
- **Strategy B:** GRC Core + Wayfold Regulatory Engine (servizi esterni via API)

## Layout

```text
apps/wayfold-compliance/
  docs/         stato, decisioni, evaluation, architecture
  automation/   overnight orchestrator
  prompts/      transition + phase prompts
  .wayfold/     state / config / results
  vendor/       clone OSS (gitignored) — solo macchina locale
```

## Overnight (unattended)

```powershell
.\apps\wayfold-compliance\automation\overnight.ps1
```

PC acceso, rete attiva, Cursor autenticato (`agent login`). Nessun deploy production automatico.

## Avvio core locale

Vedi comandi in `docs/PROGRESS.md`.

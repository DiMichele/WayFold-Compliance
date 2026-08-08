# WayFold Compliance

Applicativo privato GRC multi-framework per consulenza cybersecurity.

- Dominio previsto: `compliance.wayfold.xyz`
- Repository: [DiMichele/WayFold-Compliance](https://github.com/DiMichele/WayFold-Compliance)
- Stato: **Phase -1 / Phase 0 COMPLETE** — core selezionato, demo Michele PASS
- Raccomandazione: [`docs/PHASE0-RECOMMENDATION.md`](docs/PHASE0-RECOMMENDATION.md)
- Progress: [`docs/PROGRESS.md`](docs/PROGRESS.md)

## Decisione Phase 0

- **Core:** CISO Assistant Community
- **Strategy B:** GRC Core + Wayfold Regulatory Engine (servizi esterni via API)

## Layout

```text
.
  docs/         stato, decisioni, evaluation, architecture, recommendation
  automation/   orchestratore fasi (overnight)
  prompts/      prompt Cursor per fasi 1–6
  vendor/       clone OSS (gitignored) — solo macchina locale
```

## Avvio core locale (post Phase 0)

Vedi comandi in `docs/PROGRESS.md`.

# WayFold Compliance

**WayFold Compliance** — GRC multi-framework per consulenza cybersecurity.

- Produzione: https://compliance.wayfold.xyz
- Progress: [`docs/PROGRESS.md`](docs/PROGRESS.md)
- UI: [`docs/ui.md`](docs/ui.md)
- Unified Compliance: [`docs/unified-compliance.md`](docs/unified-compliance.md)
- Consultant UX: [`docs/consultant-ux.md`](docs/consultant-ux.md)

Il brand del prodotto è **solo WayFold Compliance**. Il motore GRC sottostante è un dettaglio di implementazione (Strategy B): non compare in UI, titoli o messaggi rivolti all’utente.

## Layout

```text
.
  docs/         stato, decisioni, architecture
  engine/       prodotto WayFold Compliance (UI + servizi)
  deploy/       produzione su compliance.wayfold.xyz
  automation/   orchestratore fasi (overnight)
  prompts/      prompt Cursor per fasi 1–6
```

## Deploy

```powershell
powershell -ExecutionPolicy Bypass -File apps/wayfold-compliance/deploy/deploy-compliance.ps1 -SetupTls
```
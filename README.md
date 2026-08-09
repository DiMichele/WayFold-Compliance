# WayFold Compliance

Applicativo privato GRC multi-framework per consulenza cybersecurity.

| | |
|---|---|
| Live | https://compliance.wayfold.xyz/ |
| Repository | https://github.com/DiMichele/WayFold-Compliance |
| Product realignment report | [docs/review/PRODUCT-REALIGNMENT.md](docs/review/PRODUCT-REALIGNMENT.md) |
| Review URL manifest | [docs/review/FINAL-REVIEW-URLS.md](docs/review/FINAL-REVIEW-URLS.md) |
| Screenshots | [docs/review/realign/](docs/review/realign/) · [docs/review/final/](docs/review/final/) |

## Stato

**Product realignment COMPLETE** — Knowledge Base authoring end-to-end dalla UI  
(CREATE → MAP → PUBLISH → ASSIGN → ASSESS)

- READY FOR EXTERNAL REVIEW: **YES**
- READY FOR REAL CLIENT DATA: **NO** (temporary review credential + MFA pending)

## Layout

```
.
  docs/         decisioni, architecture, review pack, acceptance
  engine/       WayFold Compliance engine (UI + API + overlay stores)
  deploy/       Docker / nginx / sync VPS
  automation/   orchestratore fasi
  prompts/      prompt Cursor storici fasi 1–6
```

## Avvio locale

Vedi `docs/PROGRESS.md` e `docs/deployment.md`.

## Deployed SHA (VPS sync)

`dab74ce204fcbfffa6e58a6d4942f1f27c0e1feb`

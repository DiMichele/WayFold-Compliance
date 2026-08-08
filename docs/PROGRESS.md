# PROGRESS — WayFold Compliance

## Fase corrente

**Phase 0 COMPLETE.**  
**Phase 1 — Working Core** pronta per **verifica indipendente** (prima transizione overnight `1_TO_2`). Non dichiarare Phase 1 COMPLETE fino a PASS + tag.

## Completato

- Scaffold `apps/wayfold-compliance/`
- Phase -1 discovery + scorecard (`open-source-evaluation.md`)
- Phase 0 decision gate: core **CISO Assistant Community**, Strategy B (`DECISIONS.md`, `architecture.md`, `PHASE0-RECOMMENDATION.md`, `gap-report.md`)
- Demo Michele registrata come PASS in raccomandazione Phase 0
- Vendor OSS locale (gitignored)
- Overlay automazione overnight installato e hardenizzato (transition-based)

## Cosa funziona

- Selezione core + architettura Strategy B documentata
- Seed/demo helpers in `docs/michele_demo_seed.py` (se usato in locale)
- Orchestratore: doctor / preflight / dry-run / unit test (pipeline reale non ancora avviata)

## Cosa non funziona / gate aperti

- Phase 1 non ancora chiusa da verification report indipendente (`PHASE1-VERIFICATION.md` assente finché non gira `1_TO_2`)
- Overnight richiede `agent login` (o `CURSOR_API_KEY`)

## Stato DB

- DB prodotto non versionato nel repo; DB vendor locali sotto `vendor/` (gitignored)

## Migrazioni recenti

- Nessuna migration prodotto WayFold in repo

## Comandi di avvio

- Core CISO: compose ufficiale in `vendor/ciso-assistant-community` (locale)
- Automazione: `.\apps\wayfold-compliance\automation\overnight.ps1`

## Git

- Remote: https://github.com/DiMichele/WayFold-Compliance
- Cartella locale: `apps/wayfold-compliance/` (repo git annidato, come Bills)
- `vendor/` non versionato

## Problemi aperti

- Auth Cursor Agent CLI per unattended overnight
- Consolidare eventuali gap Phase 1 emersi in verifica

## Technical debt

- Nessuno bloccante noto a livello automazione

## Prossimo step consigliato

1. `agent login`
2. `.\apps\wayfold-compliance\automation\overnight.ps1 -Command preflight`
3. Overnight → **Verify/Close Phase 1 → Develop Phase 2**

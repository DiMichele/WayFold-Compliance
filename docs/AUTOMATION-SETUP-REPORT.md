# WAYFOLD OVERNIGHT AUTOMATION — Setup Report

Generated during automation install/harden session. Pipeline reale **non** avviata.

## STATUS

`READY_FOR_OVERNIGHT_RUN` (sistema) con **USER ACTION REQUIRED** prima del go-live.

## MODE

`LOCAL`

Cloud automation non configurata/verificata (`agent worker` esiste ma non collegato a questo workflow).

## BUNDLE

Installed: **YES** (overlay root, no overwrite of existing docs)

## CURRENT BRANCH

`main` (overnight creerà/userà `automation/wayfold-compliance`)

## INITIAL STATE

- Implemented Phase: `1` (soggetta a verify)
- Last Closed Phase: `0`
- Next Transition: `1_TO_2`
- Status: `READY`

## FIRST REAL RUN

Verify/Close Phase 1 -> Develop Phase 2

## CURSOR

- CLI: **PASS** (`agent` 2026.08.04, Windows `agent.cmd`)
- Auth: **USER ACTION REQUIRED** (`agent login` oppure `CURSOR_API_KEY`)

## GITHUB

- Remote: `https://github.com/DiMichele/WayFold.git`
- Push auth: **PASS** (dry-run ok)
- Main branch: `main`
- Auto merge: **ENABLED**
- `gh` CLI: non loggato (opzionale; git push funziona)

## CONFIG

- autoCommit: true
- autoPush: true
- autoTag: true
- autoMergeMain: true
- maxAutomaticFixAttempts: 3
- autoDeploy: absent/forbidden

## ORCHESTRATOR TESTS

14/14 PASS (`test_orchestrator.py`)

## DRY RUN

PASS (happy path, 3x fail human review, push fail, final regression fail, invalid JSON, merge conflict, interrupt resume)

## PREFLIGHT

FAIL fino a Cursor auth (+ eventuali dirty tracked fuori compliance: `.cursor/rules/deploy.mdc`, root `README.md`)

## ONE COMMAND TO START

```powershell
.\apps\wayfold-compliance\automation\overnight.ps1
```

```bash
./apps/wayfold-compliance/automation/overnight.sh
```

## CAN I TURN OFF THE PC?

**NO**

## IF EVERYTHING PASSES

Verify/close phases 1-6 with independent agent sessions, tags, pushes, final regression, merge+push `main`, status `COMPLETE`.

## IF SOMETHING FAILS

Stop, save, commit, push branch, diagnostic reports, `HUMAN_REVIEW_REQUIRED`. No blind continue. No production deploy.

## USER ACTION REQUIRED BEFORE START

1. `agent login` (browser) **oppure** set `CURSOR_API_KEY`
2. Disabilita sleep del PC
3. Stash/commit modifiche tracked non-compliance (`README.md`, `.cursor/rules/deploy.mdc`) se preflight le segnala
4. (Consigliato) assicurati che Phase 1 Working Core sia nello stato che vuoi far verificare
5. Lancia overnight e vai a dormire

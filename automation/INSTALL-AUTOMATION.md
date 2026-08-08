# WayFold Compliance — INSTALL AUTOMATION

## Quick Start (5 step)

1. Apri un terminale nella **root** del repository WayFold (PowerShell o bash).
2. Autenticati a Cursor Agent CLI: `agent login` (una tantum).
3. Assicurati che Phase 1 sia implementata e che il working tree sia compreso (`git status`).
4. Lancia **un solo comando**:
   - Windows: `.\apps\wayfold-compliance\automation\overnight.ps1`
   - bash: `./apps/wayfold-compliance/automation/overnight.sh`
5. Lascia il PC **acceso**, in rete, senza sleep. Al mattino leggi `docs/AUTOMATION-RUN-REPORT.md`.

`overnight` esegue già preflight + doctor. Non chiede continue/approve.

---

## Cosa fa la pipeline

```text
VERIFY Phase N (+ fix/reverify ≤3)
→ CLOSE Phase N + tag phase-N-complete
→ DEVELOP Phase N+1
→ commit + push
→ NEW agent session
→ … fino a Phase 6
→ FINAL REGRESSION
→ merge su main + push main
→ COMPLETE
```

oppure fail-closed:

```text
HUMAN_REVIEW_REQUIRED → commit + push + report → STOP
```

Una fase **non** viene verificata nello stesso agent run che l’ha sviluppata.

---

## Prerequisiti

| Componente | Note |
|---|---|
| Python 3.10+ | `python` / `python3` |
| Git + push su `origin` | già verificabile con dry-run |
| Cursor Agent CLI | `irm 'https://cursor.com/install?win32=true' \| iex` oppure curl install |
| Auth Cursor | `agent login` **oppure** `CURSOR_API_KEY` |
| Docker | necessario per verificare il core CISO in Phase 1 |
| Branch | overnight crea/usa `automation/wayfold-compliance` |

**MODE:** `LOCAL_OVERNIGHT` — il PC deve restare acceso. Cloud automation non è configurata.

**NON** fa deploy su `compliance.wayfold.xyz`.

---

## Comandi utili

```powershell
.\apps\wayfold-compliance\automation\overnight.ps1 -Command doctor
.\apps\wayfold-compliance\automation\overnight.ps1 -Command preflight
.\apps\wayfold-compliance\automation\overnight.ps1 -Command status
.\apps\wayfold-compliance\automation\overnight.ps1 -Command dry-run
python apps/wayfold-compliance/automation/test_orchestrator.py
```

```bash
python3 apps/wayfold-compliance/automation/wayfold_orchestrator.py doctor
python3 apps/wayfold-compliance/automation/wayfold_orchestrator.py overnight
```

---

## Recovery Guide

| Sintomo | Cosa è successo | Dove guardare | Resume sicuro |
|---|---|---|---|
| `HUMAN_REVIEW_REQUIRED` | Gate fallito dopo retry | `state.json`, `PHASE*-VERIFICATION.md`, `AUTOMATION-RUN-REPORT.md` | Correggi a mano → `reset --transition …` o ripristina `status=READY` con cautela → `overnight` |
| Cursor auth failure | CLI non loggata | `agent status` | `agent login` → `overnight` |
| GitHub push failure | credenziali/remote | log orchestratore, `git push` | Ripristina auth → `overnight` (resume da state) |
| CI failure | check GitHub rossi sulla branch | Actions | Fix → push → continua overnight |
| Merge conflict | main diverge | `git status` su tentativo merge | Risolvi su branch automation → non force-push |
| Invalid agent result | JSON assente/invalid | `.wayfold/results/`, logs | Fix prompt/output → `overnight` |
| Docker failure | core non avviabile | log Docker / vendor CISO | Ripristina ambiente → resume |
| Destructive migration blocker | migration non additive | PROGRESS / agent report | Review umana obbligatoria |
| Interrupted run | CTRL+C / kill | `status=INTERRUPTED` | `overnight` riprende (resume) |

Non usare `git reset --hard` / `git clean -fd` come prima scelta.

---

## Config

`apps/wayfold-compliance/.wayfold/config.json`:

- `autoCommit` / `autoPush` / `autoTag` / `autoMergeMain` = true
- `maxAutomaticFixAttempts` = 3
- **nessun** `autoDeploy`

---

## Stato iniziale atteso

```json
{
  "lastClosedPhase": 0,
  "implementedPhase": 1,
  "nextTransition": "1_TO_2",
  "status": "READY"
}
```

Prima attività reale: **Verify/Close Phase 1 → Develop Phase 2**.

# WayFold Compliance Automation State Machine

## Transition model (obbligatorio)

```text
Agent session N:   VERIFY Phase K (+fix≤3) → CLOSE K → DEVELOP K+1 → STOP
Agent session N+1: VERIFY Phase K+1 → …
```

Phase K non è mai verificata nello stesso agent run che l’ha sviluppata.

## Stati

```text
READY
VERIFYING
FIXING
DEVELOPING
AWAITING_VERIFICATION
BLOCKED
HUMAN_REVIEW_REQUIRED
FINAL_REGRESSION
MERGING
COMPLETE
INTERRUPTED
```

## Transizioni

| nextTransition | Verify | Develop |
|---|---|---|
| 1_TO_2 | 1 | 2 |
| 2_TO_3 | 2 | 3 |
| 3_TO_4 | 3 | 4 |
| 4_TO_5 | 4 | 5 |
| 5_TO_6 | 5 | 6 |
| CLOSE_6 | 6 | — → FINAL_REGRESSION |

Dopo PASS di `1_TO_2`:

```json
{ "lastClosedPhase": 1, "implementedPhase": 2, "nextTransition": "2_TO_3", "status": "READY" }
```

Dopo PASS finale + merge:

```json
{ "lastClosedPhase": 6, "implementedPhase": 6, "nextTransition": null, "status": "COMPLETE" }
```

## Trust boundary

L’orchestratore decide solo da JSON in `.wayfold/results/`.
Testo libero dell’agente non autorizza PASS.
JSON invalid → `HUMAN_REVIEW_REQUIRED` (fail closed).

## Lock / interrupt

- Lock: `.wayfold/orchestrator.lock` (stale lock gestito con check PID)
- CTRL+C → `INTERRUPTED` (recuperabile con nuovo `overnight`)

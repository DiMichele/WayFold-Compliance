# Phase 6 — Automated Evidence — Independent Verification

Non correggere codice prodotto.

## Gate

Verifica:

- adapter/connector boundary pulito;
- ingest fixture/Prowler result riproducibile;
- normalizzazione finding/check;
- mapping al controllo corretto;
- evidence automatica usa il motore esistente;
- provenance/source/timestamp presenti;
- ingest ripetuto non crea duplicazioni incontrollate;
- cross-tenant denied;
- segreti non compaiono in repo/log/result;
- failure esterna non corrompe stato;
- technical PASS non marca automaticamente requirement/framework compliant;
- demo manual+automated evidence;
- regression completa Phase 1-5.

Se l'ambiente impedisce una scansione reale ma la fixture dimostra correttamente il boundary, distinguere environment blocker da product blocker secondo le decisioni di progetto.

Scrivi `{{VERIFY_REPORT_PATH}}`.

## Verdict

Solo `PASS`, `FAIL`, `BLOCKED`.

Un PASS della Phase 6 chiude la pipeline automatizzata corrente; non inventare Phase 7.

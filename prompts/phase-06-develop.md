# Phase 6 — Automated Evidence — Development

Obiettivo: introdurre una prima integrazione reale di evidence tecnica automatica senza trasformare WayFold in un motore CSPM completo.

## Strategia

Riutilizzare Prowler o un adapter equivalente come specialized component quando coerente con le decisioni precedenti. Non duplicare il motore di scan cloud.

## Boundary

Creare un'integrazione esplicita:

`External scanner -> normalized finding/check -> mapping to canonical/control -> evidence/update suggestion`.

Non scrivere direttamente nel DB di un tool esterno e non accoppiare i modelli interni ai dettagli del provider.

## MVP

Implementare almeno:

- connector/adapter configuration;
- import/ingest di un risultato tecnico controllato (fixture o Prowler output reale se ambiente disponibile);
- normalizzazione finding/check;
- mapping a uno o più controlli;
- evidence record/proof riusando il motore evidence esistente;
- timestamp/source/check metadata;
- stato stale/last checked quando sensato;
- manual review quando il finding non è sufficiente a determinare implementazione.

## Regola importante

Un technical check PASS non deve automaticamente significare che un intero requirement organizzativo è compliant. Deve essere evidence/supporting signal secondo il modello Unified Compliance.

## Operabilità

- credenziali mai persistite in chiaro nel codice;
- timeout/failure isolated;
- idempotenza ingest;
- deduplicazione dei risultati periodici;
- audit/provenance della evidence automatica.

## Demo

Dimostrare almeno un controllo con:

- evidence manuale;
- evidence tecnica automatica;
- source/check identificabile;
- aggiornamento successivo senza duplicazioni incontrollate.

Se Prowler reale non è eseguibile nell'ambiente, usare fixture ufficialmente compatibile e documentare l'environment blocker; non inventare un nuovo scanner.

## Test

- ingest idempotente;
- mapping finding->control;
- tenant isolation;
- secret handling;
- failure scanner non corrompe evidence;
- PASS tecnico non auto-setta compliance globale;
- regression Phase 1-5.

## Machine result

`AWAITING_VERIFICATION` o `BLOCKED`.

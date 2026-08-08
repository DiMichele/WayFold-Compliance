# Phase 1 — Independent Verification & Closure Gate

Agisci come reviewer avversariale. NON partire dal presupposto che Phase 1 sia corretta.

## Divieto importante

Durante questo run NON correggere codice prodotto. Puoi:

- leggere codice;
- eseguire comandi/test;
- creare/aggiornare `{{VERIFY_REPORT_PATH}}`;
- aggiornare documentazione di verifica;
- scrivere il result JSON.

Se trovi un bug, segnalalo come FAIL: sarà un fix agent separato a correggerlo.

## Ricostruisci gli acceptance criteria

Verifica almeno:

- core selezionato realmente avviabile;
- client/tenant;
- program/perimeter/assessment;
- framework/requirements;
- controls o concetto equivalente;
- client implementation;
- evidence;
- task/remediation;
- owner/deadline se previsti;
- RBAC;
- tenant isolation;
- demo Michele;
- migrations/setup pulito;
- test/build.

## Review avversariale

Cerca:

- TODO/FIXME/HACK/stub/mock/demo-only incompatibili con la fase;
- dati hardcoded;
- bypass RBAC;
- query non scoped al tenant;
- evidence cross-tenant;
- duplicazioni inutili rispetto al core;
- migrazioni non riproducibili;
- errore tra documentazione e codice reale.

## Demo replay

Riproduci, per quanto possibile da dataset pulito/controllato:

`Michele Demo -> Cyber Compliance Demo -> framework -> controls -> status -> owner -> deadline -> evidence -> task -> assessment/dashboard`.

Segna ogni voce PASS/FAIL nel report.

## Gate

Il verdict deve essere binario:

- `PASS` — tutti i criteri bloccanti sono soddisfatti;
- `FAIL` — uno o più criteri Phase 1 sono realmente rotti/incompleti;
- `BLOCKED` — impossibile verificare per blocker esterno/ambiente che richiede intervento umano.

Crea `{{VERIFY_REPORT_PATH}}` con acceptance matrix, test, demo replay, security/RBAC, tenant isolation, build e problemi non bloccanti.

## Machine result

`status` ammessi: `PASS`, `FAIL`, `BLOCKED`.

# Phase {{PHASE}} — Fix dopo verifica fallita

## Obiettivo

Correggi esclusivamente i difetti trovati dall'ultimo verification run della Phase {{PHASE}} e porta nuovamente l'implementazione nello stato `AWAITING_VERIFICATION`.

## Prima di modificare codice

1. leggi `{{VERIFY_REPORT_PATH}}`;
2. leggi il più recente result JSON di verifica in `apps/wayfold-compliance/.wayfold/results/`;
3. ricostruisci l'elenco esatto dei failure;
4. verifica che ogni failure appartenga realmente allo scope Phase {{PHASE}}.

## Regole

- Non iniziare la fase successiva.
- Non ampliare lo scope.
- Non mascherare un problema con dati hardcoded/mock.
- Non cambiare architettura o core per aggirare un bug senza una motivazione documentata.
- Correggi la causa, non solo il test.
- Se un finding del verifier è errato, dimostralo con codice/test e documentalo; non ignorarlo silenziosamente.
- Riesegui tutti i test/regression gate pertinenti, non solo il test che prima falliva.

## Output documentale

Aggiorna `{{PROGRESS_PATH}}` con:

- fix applicati;
- test rieseguiti;
- eventuali blocker residui.

## Machine result

Valori ammessi per `status`:

- `AWAITING_VERIFICATION` — i difetti sono stati corretti e serve una nuova verifica indipendente;
- `BLOCKED` — esiste un blocker reale non risolvibile senza intervento umano/decisione architetturale.

Non usare `PASS`: il fix agent non certifica la propria correzione.

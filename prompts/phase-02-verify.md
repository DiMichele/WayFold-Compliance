# Phase 2 — Unified Compliance — Independent Verification

Agisci come reviewer avversariale. NON correggere codice prodotto durante questo run.

## Verifica fondamentale

La domanda a cui il prodotto deve rispondere è:

> Se Michele deve rispettare tre framework, cosa deve implementare una sola volta, quali requirement/framework copre ogni misura e quale delta rimane?

## Acceptance gate

Verifica realmente:

- tre framework/versioni pinned nello stesso programma;
- checklist unica generata da dati reali;
- controllo comune a A/B/C compare una sola volta;
- coverage A/B/C visibile;
- mapping PARTIAL mantiene il delta;
- controllo implementato + mapping PARTIAL non diventa FULL;
- requirement senza mapping compaiono come UNMAPPED;
- owner/deadline/evidence/task Phase 1 rimangono funzionanti;
- filtri/search principali;
- readiness per singolo framework derivata dai dati;
- control impact/high impact controls trasparente;
- tenant isolation/RBAC dei nuovi boundary;
- version pinning: non usa automaticamente latest globale;
- test/build/regression core.

## Casi di test obbligatori

1. A1 -> CTRL-01 FULL, B1 -> CTRL-01 FULL, C1 -> CTRL-01 PARTIAL; CTRL-01 IMPLEMENTED.
   Atteso: A1/B1 FULLY_COVERED, C1 PARTIALLY_COVERED.
2. B3 senza mapping -> UNMAPPED e visibile.
3. Stesso CTRL-01 in tre framework -> una sola riga/entità nella unified checklist.
4. Cross-tenant query su unified endpoint/service -> DENIED.

## Report

Scrivi `{{VERIFY_REPORT_PATH}}` con matrice PASS/FAIL, casi dati, query/test eseguiti, readiness verificata, regressioni, problemi non bloccanti.

## Verdict

`PASS`, `FAIL` o `BLOCKED` soltanto.
Non correggere i failure e non iniziare Phase 3.

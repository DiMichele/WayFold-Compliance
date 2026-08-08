# Phase 4 — Regulatory Intelligence — Independent Verification

Non correggere codice prodotto.

## Gate

Verifica con fixture/source controllata:

- Source configurabile e tenant/global scope corretto;
- fetch iniziale crea snapshot/hash;
- fetch identico non crea falsa change;
- modifica reale crea snapshot successivo e RegulatoryChange;
- diff leggibile;
- failure/timeout source non corrompe stato né blocca gli altri job;
- retry/lastChecked/lastSuccessfulFetch coerenti;
- nessuna FrameworkVersion PUBLISHED viene mutata automaticamente;
- nessun programma cliente viene migrato automaticamente;
- change -> requirement/control/client impact funziona quando esiste associazione;
- authorization sulle schermate/admin API;
- protezioni basilari su URL/fetch;
- regression Phase 1-3.

Cerca duplicazioni di change, hash instabili, fetch non idempotenti, SSRF ovvie, snapshot inconsistenti e job che falliscono globalmente per una sola source.

Scrivi `{{VERIFY_REPORT_PATH}}`.

## Verdict

Solo `PASS`, `FAIL`, `BLOCKED`.

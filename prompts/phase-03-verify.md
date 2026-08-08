# Phase 3 — Consultant UX — Independent Verification

Non correggere codice prodotto. Verifica l'esperienza come se dovessi usare WayFold domani su un vero cliente.

## Gate operativo

Usando `Michele Demo` e almeno un secondo tenant/demo quando utile, verifica:

- Portfolio mostra solo clienti autorizzati e KPI coerenti;
- Client dashboard numericamente coerente con Unified Compliance;
- Gap Assessment filtra/search/sort correttamente;
- un controllo è raggiungibile dal gap e mostra framework coverage/delta/evidence/task;
- owner view identifica workload e overdue;
- deadline view evidenzia scadute e prossimi 30 giorni;
- evidence view riusa evidence esistenti e non espone cross-tenant;
- report HTML è print-friendly e non contiene dati demo hardcoded;
- CSV corrisponde ai dati visibili;
- dataset da centinaia di righe non produce evidenti N+1 o UI inutilizzabile;
- Phase 1/2 regression suite passa.

## Review avversariale

Cerca KPI incoerenti, conteggi duplicati da mapping multi-framework, percentuali fuorvianti, query cross-tenant, export che ignora filtri/scope, dati latest invece di pinned.

Scrivi `{{VERIFY_REPORT_PATH}}`.

## Verdict

Solo `PASS`, `FAIL`, `BLOCKED`.

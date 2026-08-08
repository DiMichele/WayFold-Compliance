# Phase 5 — AI Assistance — Independent Verification

Non correggere codice prodotto.

## Gate

Con fake provider e, solo se configurato, un provider reale non obbligatorio:

- AIProvider è centralizzato/provider-agnostic;
- aiProcessingEnabled=false blocca invio di contenuti cliente;
- mapping suggestion produce structured output valido;
- suggestion resta AI_SUGGESTED finché un umano non approva;
- reject non modifica mapping;
- regulatory diff analysis non modifica FrameworkVersion;
- gap explanation non cambia status cliente;
- output malformed/provider error non corrompe dati;
- prompt minimization ragionevole;
- audit delle approval/rejection quando previsto;
- authorization corretta;
- regression Phase 1-4.

Cerca chiamate LLM dirette fuori dal service boundary, auto-apply, leakage cross-tenant, secret logging e test che dipendono da API reali.

Scrivi `{{VERIFY_REPORT_PATH}}`.

## Verdict

Solo `PASS`, `FAIL`, `BLOCKED`.

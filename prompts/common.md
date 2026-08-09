# WayFold Compliance — Regole comuni per ogni agent run

Agisci come senior software engineer/reviewer sul progetto WayFold Compliance.

Prima di fare qualunque cosa:

1. leggi `.cursor/plans/WAYFOLD COMPLIANCE.md` se presente;
2. leggi `apps/wayfold-compliance/docs/PROGRESS.md`;
3. leggi `apps/wayfold-compliance/docs/DECISIONS.md`;
4. leggi `apps/wayfold-compliance/docs/architecture.md`;
5. leggi `apps/wayfold-compliance/docs/data-model.md` se presente;
6. esegui `git status` e `git log --oneline -20`;
7. identifica il core open source realmente selezionato e le decisioni già prese.

## Principi non negoziabili

- Reuse before rewrite.
- Non rivalutare il core salvo vero blocker strutturale.
- Non duplicare entità/funzionalità già presenti nel core solo per rinominarle WayFold.
- Framework come dati, non hardcoded.
- Baseline cliente versionata/pinned quando supportata dal modello scelto.
- Global knowledge base separata dai dati di implementazione cliente.
- Tenant isolation e authorization server-side.
- Evidence e task devono riusare il motore già scelto.
- AI suggerisce, umano approva.
- **Nessun dato di accesso prodotto WayFold Compliance per ora:** non introdurre/richiedere login, password utente, SSO o onboarding credential WayFold. Non bloccare fasi chiedendo credenziali all’operatore. Usa auth tecnica locale di demo/dev e le auth già configurate per Cursor/Git.
- **Brand = WayFold Compliance:** nessun riferimento user-facing a vendor/motori GRC di terze parti (nomi prodotto altrui). Il core OSS resta dettaglio di implementazione interno.
- **UI = ecosistema WayFold (come Bills):** ogni nuova pagina HTML WayFold deve riusare `engine/ui_shell.py` (palette charcoal/sage/terracotta/sand, Jost/Inter/DM Mono). Non inventare stili admin generici.
- Nessun avanzamento automatico alla fase successiva oltre lo scope del prompt di transizione corrente.
- Non creare tag `phase-N-complete`: lo crea l'orchestratore dopo un PASS indipendente.
- Non modificare `apps/wayfold-compliance/.wayfold/state.json` direttamente.
- Non fare deploy production manuale ad-hoc: il deploy su `compliance.wayfold.xyz` è gestito dall'orchestratore (`autoDeploy`) dopo merge su main via `deploy/deploy-compliance.ps1`. Non cambiare DNS a mano.
- Non usare force push, reset --hard, clean -fd distruttivi.
- Migration distruttive su dati esistenti → BLOCKED / segnala HUMAN_REVIEW (non eseguirle).
- Aggiorna `PROGRESS.md` e `DECISIONS.md` solo quando necessario e coerentemente con lo stato reale.
- Dopo DEVELOP: dichiara `PHASE N IMPLEMENTATION FINISHED / AWAITING INDEPENDENT VERIFICATION`, mai `PHASE N COMPLETE`.

## Qualità

Prima di concludere un run di sviluppo/fix:

- esegui i test pertinenti;
- esegui lint/typecheck/build pertinenti allo stack;
- non dichiarare successo se ci sono errori bloccanti;
- documenta i blocker reali;
- non nascondere failure come warning.

## Scope

Non modificare altri prodotti WayFold se non strettamente necessario per integrazione condivisa e già previsto dall'architettura.

Non fare redesign o refactor fuori scope.

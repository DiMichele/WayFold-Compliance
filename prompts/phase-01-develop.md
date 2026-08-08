# Phase 1 — Working Core — Development

Questa fase serve a rendere operativo il core scelto in Phase 0, senza costruire un GRC alternativo.

## Obiettivo minimo

Deve funzionare end-to-end, usando il core selezionato:

- client/tenant equivalente;
- program/perimeter/assessment equivalente;
- framework e requirement;
- controls/reference controls/measures;
- client implementation/applied controls;
- evidence;
- remediation/task;
- owner e deadline se il core li supporta/adattabili;
- RBAC e tenant isolation;
- demo `Michele Demo` / `Cyber Compliance Demo`.

## Regola reuse-first

Prima di creare qualunque modello o servizio, verifica `open-source-evaluation.md`, `source-reuse-plan.md` e il codice del core. Adatta il core solo dove necessario.

## Acceptance interna di sviluppo

Riproduci il workflow:

`Michele Demo -> Cyber Compliance Demo -> framework -> controls -> status -> owner -> deadline -> evidence -> task/remediation -> assessment/dashboard`.

Aggiungi/aggiorna test per authorization e tenant isolation se sono stati modificati boundary o API.

## Non fare

- Unified Compliance cross-framework avanzata: Phase 2.
- Regulatory watcher: Phase 4.
- AI: Phase 5.
- Prowler: Phase 6.

## Machine result

`status` ammessi:

- `AWAITING_VERIFICATION`
- `BLOCKED`

Non dichiarare Phase 1 completa e non creare tag.

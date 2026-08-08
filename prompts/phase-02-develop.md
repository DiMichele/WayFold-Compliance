# Phase 2 — Unified Compliance — Development

Questa è la prima vera capability distintiva WayFold.

## Obiettivo

Dato un programma cliente con più framework/versioni, produrre una checklist unica basata sui controlli/misure comuni, mantenendo visibili origine normativa, relazioni, delta e requirement non mappati.

Esempio concettuale:

`REQ-A1 + REQ-B7 + REQ-C2 -> CTRL-IAM-001` una sola implementazione cliente.

## Prima di creare modelli

Rileggi il modello del core scelto. Riutilizza concetti semanticamente equivalenti a CanonicalControl, AppliedControl/Measure, RequirementAssessment e Mapping. Non creare tabelle duplicate per naming.

## Mapping

Supportare, direttamente o tramite adapter coerente col core:

- FULL
- PARTIAL
- SUPPORTING

Con metadata sufficienti per almeno rationale e uncovered delta. Preservare i delta specifici del framework.

## Unified checklist service

Business logic in service/application layer, non UI. Deve:

1. usare le framework version pinned del programma;
2. recuperare requirements applicabili/leaf;
3. recuperare mapping validi;
4. risolvere controlli/misure condivisi;
5. deduplicare;
6. conservare coverage e delta per framework;
7. identificare UNMAPPED requirements;
8. produrre input per readiness e control impact.

## UI

Integra nei pattern UI del core una vista professionale con almeno:

- Control
- Status
- Framework coverage
- Owner
- Deadline
- Priority
- Evidence
- Tasks
- Gap/delta

Filtri minimi: framework, status, owner, priority, deadline, mapping/partial, missing evidence.

## Readiness

Per requirement distinguere almeno:

- FULLY_COVERED
- PARTIALLY_COVERED
- NOT_COVERED
- UNMAPPED
- NOT_APPLICABLE

Un mapping PARTIAL con controllo implementato resta PARTIALLY_COVERED finché il delta non è esplicitamente coperto. Non assumere PARTIAL + PARTIAL = FULL.

## Control impact

Mostrare in modo trasparente quali controlli impattano più requirement scoperti e più framework. Evitare score arbitrari opachi; preferire metriche leggibili tipo “5 requirement scoperti su 3 framework”.

## Demo obbligatoria

Su `Michele Demo` predisporre almeno 3 framework con:

- un controllo condiviso da tutti e tre;
- un mapping PARTIAL con delta;
- un controllo condiviso da due framework;
- almeno due requirement UNMAPPED;
- stati misti IMPLEMENTED / IN_PROGRESS / NOT_IMPLEMENTED.

## Test critici

- deduplicazione 3 framework -> 1 controllo;
- partial resta partial;
- unmapped resta visibile;
- version pinning;
- tenant isolation sui nuovi endpoint/service;
- nessun bypass RBAC;
- performance ragionevole senza N+1 evidenti.

## Documentazione

Crea/aggiorna `apps/wayfold-compliance/docs/unified-compliance.md`, `PROGRESS.md`, `architecture.md`, `data-model.md` e ADR solo per decisioni non banali.

## Fuori scope

Niente AI, scraper/regulatory watcher, Prowler, nuovo auth/evidence/task engine, redesign globale.

## Machine result

`status`: `AWAITING_VERIFICATION` oppure `BLOCKED`.
Non creare tag e non iniziare Phase 3.

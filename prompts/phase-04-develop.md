# Phase 4 — Regulatory Intelligence — Development

Obiettivo: monitorare fonti configurate, rilevare cambiamenti reali e trasformarli in una inbox di RegulatoryChange senza modificare automaticamente framework o clienti.

## Modello / capability

Riutilizza il core dove esiste. Aggiungi solo ciò che manca per:

- Source configurabile via web;
- monitoring enabled + frequenza;
- fetch strategy/adapters;
- SourceSnapshot;
- normalized content/hash;
- diff;
- RegulatoryChange inbox;
- collegamento manuale/deterministico a requirement/control potenzialmente impattati;
- client impact derivato dai mapping/program pinned.

## Adapter boundary

Separare chiaramente:

`fetch -> normalize -> hash -> compare -> diff -> impact projection`.

Prevedere adapter almeno per HTML e una base estendibile per PDF/JSON/RSS/API. Non costruire uno scraper monolitico basato su selector fragili.

## Change semantics

Un cambio cosmetico HTML non deve automaticamente diventare modifica normativa. Conservare raw/normalized metadata sufficienti per diagnosi e deduplicazione.

## Workflow

`Source -> Fetch -> Snapshot -> Compare -> Change detected -> RegulatoryChange NEW -> review -> ACCEPTED/IGNORED`.

Nessuna modifica automatica di FrameworkVersion pubblicate o programmi cliente.

## Client impact

Per una change associata a requirement/versioni, mostrare quali controlli e quali clienti/programmi pinned potrebbero essere impattati. È un'indicazione operativa, non una migrazione automatica.

## Jobs

Usare queue/scheduler già esistente o boundary minimale coerente. Retry/backoff e timeout ragionevoli. Una source fallita non deve bloccare tutto il worker.

## Security/operability

- URL validate;
- timeout e size limits;
- evitare fetch arbitrari verso network interno quando applicabile;
- logs senza contenuti sensibili inutili;
- health/last successful fetch visibile.

## Demo

Creare almeno una source demo controllabile/local fixture che consenta di dimostrare:

1. snapshot iniziale;
2. contenuto modificato;
3. nuovo hash;
4. diff/change NEW;
5. review;
6. impatto su requirement/control/client demo.

Non dipendere da un sito esterno instabile per i test automatici.

## Fuori scope

Niente LLM/embeddings: Phase 5. Niente Prowler: Phase 6.

## Machine result

`AWAITING_VERIFICATION` o `BLOCKED`.

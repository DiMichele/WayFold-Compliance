# Phase 3 — Consultant UX — Development

Obiettivo: trasformare il core + Unified Compliance in uno strumento realmente usabile ogni giorno da un consulente, senza costruire nuove capability di dominio fuori scope.

## Deliverable principali

### Portfolio dashboard
Vista globale clienti/programmi con almeno:

- cliente;
- programmi attivi;
- framework;
- implementation readiness sintetica;
- gap critici/high priority;
- task scaduti;
- prossima deadline;
- ultima attività.

### Client dashboard
Per un cliente mostrare:

- framework/versioni;
- raw requirements;
- unified controls;
- implemented/in progress/not implemented/N/A;
- unmapped;
- evidence mancanti/in scadenza;
- task aperti/scaduti;
- deadline prossimi 30 giorni;
- readiness per framework;
- workload per owner.

### Gap Assessment
Tabella professionale, densa e filtrabile:

- Framework
- Requirement
- Control
- Mapping
- Status
- Owner
- Deadline
- Evidence
- Gap
- Notes

Filtri: framework, status, owner, priority, deadline, mapped/unmapped, evidence missing.

### Owner / Deadline views
Permettere di capire rapidamente chi deve fare cosa e quando. Riutilizzare Task/Stakeholder/Implementation esistenti.

### Evidence view
Vista operativa delle evidence già esistenti, con controlli collegati e scadenza/validità se il modello la supporta.

### Reports
MVP: report HTML print-friendly + CSV. Deve includere executive overview, framework readiness, gap prioritari, controls in progress, overdue, upcoming deadlines, unmapped.

## UX rules

- integra nei pattern del core;
- tabelle dense, search, filtri, sticky header/virtualization o pagination se serve;
- niente marketing dashboard/gradienti/card giganti;
- niente nuovo motore report se il core ne ha uno estendibile;
- nessun dato hardcoded.

## Performance

Le viste devono restare utilizzabili con ~500 controlli/program e migliaia di requirement globali.

## Test

- portfolio non mostra tenant non autorizzati;
- filtri producono risultati coerenti;
- report usa dati reali del programma pinned;
- drill-down dashboard -> gap/control corretto;
- evidence/task/owner counts coerenti con sorgente dati;
- regression Phase 1/2.

## Fuori scope

Niente watcher, AI, Prowler, nuovo risk/vendor/asset engine.

## Machine result

`AWAITING_VERIFICATION` o `BLOCKED`.
Non dichiarare Phase 3 completa.

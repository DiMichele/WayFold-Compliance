# WayFold Compliance — Design System

Riferimento visuale: `wayfold-compliance-definitive-mockup.html` (questa cartella).

Implementazione runtime: `engine/ui_shell.py`, `engine/ui_icons.py`, `engine/ui_labels.py`, `engine/ui_components.py`, `engine/i18n.py`.

## Principi

- Desktop-first, data-oriented, alta densità informativa
- Sobrio e professionale (uso quotidiano GRC)
- Navy sidebar + superfici chiare + accento viola WayFold
- Dati reali (mai metriche/clienti del mockup hardcodati)
- Interfaccia in italiano (default); EN opzionale via `?lang=`
- Icone esclusivamente SVG (nessun emoji / Unicode come icona)

## Palette (token)

| Token | Valore | Uso |
|---|---|---|
| `--wf-bg` | `#f5f7fb` | Sfondo app |
| `--wf-surface` | `#ffffff` | Panel / tabelle |
| `--wf-surface-2` | `#fafbfc` | Header tabella |
| `--wf-border` | `#e2e7ef` | Bordi |
| `--wf-ink` | `#151b2b` | Testo primario |
| `--wf-muted` | `#6f7a8e` | Meta / subtitle |
| `--wf-sidebar` | `#101522` | Sidebar |
| `--wf-primary` | `#675cf2` | Accento WayFold |
| `--wf-success` | `#17834b` | Implementato / ok |
| `--wf-warning` | `#a76308` | In corso / parziale |
| `--wf-danger` | `#b42318` | Critico / scaduto |
| `--wf-info` | `#2563d8` | Informativo |
| `--wf-violet` | `#7c3aed` | Draft / AI / support |

## Typography

- Family: Inter / system-ui
- Page title: ~26px
- Panel title: 13px
- Body / table: 12.5–14px
- Metadata: 11–12px

## Spacing / radius / shadow

- Scala: 4 · 8 · 12 · 16 · 20 · 24 · 32
- Radius: button/input 8–9px · card/panel 12px
- Shadow: quasi invisibile (`--wf-shadow-xs` / `--wf-shadow-sm`); più presente solo su drawer/modal

## Shell

- **Sidebar** scura sticky, sezioni: Area di lavoro · Knowledge Base · Amministrazione
- **Topbar** compatta: breadcrumb WayFold › pagina (nessuna fake search / CTA non implementata)
- **Page header**: eyebrow · titolo · descrizione operativa · azioni

## Componenti condivisi

| Componente | Modulo |
|---|---|
| App shell / sidebar / topbar | `ui_shell.render_shell` |
| Icone SVG | `ui_icons.icon` / `icon_for_path` |
| PageHeader / MetricCard / Panel | `ui_components` |
| StatusBadge / MappingBadge / PriorityBadge | `ui_components` + `ui_labels` |
| ProgressBar / EmptyState / Framework chips | `ui_components` |
| Label IT/EN | `i18n.t` |
| Date IT | `dates.format_display_date` |

## Status mapping (UI)

| Backend | UI IT | Variant |
|---|---|---|
| IMPLEMENTED | Implementato | success |
| IN_PROGRESS | In corso | warning |
| NOT_IMPLEMENTED | Non implementato | danger |
| NOT_APPLICABLE | Non applicabile | neutral |
| FULL | Completa | success |
| PARTIAL | Parziale | warning |
| SUPPORTING | Di supporto | violet |
| DRAFT | Bozza | violet |
| APPROVED | Approvato | success |
| REJECTED | Rifiutato | danger |

Centralizzati in `engine/ui_labels.py` — non usare ternari sparsi nei componenti.

## Terminologia italiana (estratto)

| Concetto | UI |
|---|---|
| Unified controls | Controlli unificati |
| Gap assessment | Analisi dei gap |
| Tasks | Attività |
| Evidence | Evidenze |
| Owner | Responsabile |
| Due date | Scadenza |
| Implementation readiness | Avanzamento / Stato di implementazione |
| Client workspace | Area cliente |
| Regulatory intelligence | Intelligence normativa |

Non tradurre: ISO/IEC 27001, NIS2, PSNC, DORA, AI Act, brand WayFold.

## Screen inventory

| Pagina | Route | Componenti principali |
|---|---|---|
| Portfolio | `/portfolio` | MetricCard, tabella clienti, progress |
| Area cliente | `/client` | Client summary, framework cards, readiness |
| Controlli unificati | `/checklist` | DataTable densa, coverage pills, status badge |
| Dettaglio controllo | `/control` | Detail grid, mapping cards + delta |
| Analisi dei gap | `/gaps` | Gap summary, FilterBar, DataTable |
| Attività | `/tasks` | DataTable (lista; Kanban non forzato) |
| Evidenze | `/evidence` | DataTable repository |
| Report | `/report` | Report preview professionale |
| Fonti / Intelligence | `/sources`, `/changes` | Inbox normativa, diff |
| Impostazioni AI | `/ai/settings` | Form sobrio |
| Connettori / Evidenze auto | `/connectors`, `/auto-evidence` | Tabelle dense |

## Dark mode

Non implementato sul content area. La sidebar scura fa parte del design light.

## Accessibilità

- Focus visible viola soft
- `aria-label` su icon button / row action
- Status non affidato solo al colore (testo badge)
- Semantic landmarks: `aside`, `nav`, `main`, breadcrumb

## Responsive

Ottimizzato 1280 / 1440 / 1600+. Sotto 980px sidebar icon-only. Tabelle con scroll orizzontale.

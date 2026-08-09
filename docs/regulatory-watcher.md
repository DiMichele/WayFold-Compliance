# Regulatory Intelligence — WayFold Phase 4

## Goal

Monitor configured sources, detect real content changes, open a `RegulatoryChange` inbox, project client impact — **without** auto-mutating published CISO libraries or pinned client baselines. No AI (Phase 5).

## Pipeline

```text
Source → fetch (adapter) → normalize → hash → compare → diff
       → RegulatoryChange (NEW) → human review (ACCEPTED|IGNORED)
       → FrameworkUpdateSuggestion (CLONE_DRAFT)  [metadata only]
       → Client impact projection (indication)
```

Cosmetic HTML/script/style churn (raw hash changes, normalized hash stable) does **not** create a change by default.

## Engine store (not CISO DB)

`engine/data/regulatory/` (gitignored runtime):

- `sources.json`
- `snapshots.json`
- `changes.json`
- `framework_suggestions.json`
- `blobs/` raw + normalized content

## Modules

```text
engine/regulatory/
  domain.py      Source / Snapshot / Change / Suggestion / Impact
  fetch.py       URL validation, timeout, size limits, fixture/file/http
  normalize.py   HTML text extract, JSON canonical, text collapse
  hashutil.py    SHA-256
  diff.py        unified diff + relevance classify
  store.py       JSON engine store
  pipeline.py    check_source / review_change / monitoring pass
  impact.py      pinned program impact projection
  demo.py        local fixture demo cycle
  pages.py       dense HTML inbox
```

## Adapters

| Type | Support |
|---|---|
| HTML | normalize + fixture/http |
| JSON | normalize sort_keys |
| FILE / fixture:// | local demo (preferred for tests) |
| PDF / RSS / API | typed + extensible boundary (fetchers stub via same URL path) |

## Demo (no external network)

```powershell
cd apps/wayfold-compliance
python -c "from pathlib import Path; from engine.regulatory.store import RegulatoryStore; from engine.regulatory.demo import run_demo_change_cycle; from engine.regulatory.pipeline import review_change, impact_for_change; from engine.regulatory.domain import ChangeStatus; s=RegulatoryStore(Path('_tmp_reg')); c=run_demo_change_cycle(s); print(c); ch=c['changed'].change_id; print(impact_for_change(ch,s,is_superuser=True)); print(review_change(ch,s,status=ChangeStatus.ACCEPTED))"
python -m engine.tests.test_regulatory
```

Fixture files: `engine/fixtures/regulatory/demo-nis2/v1.html` → `v2.html` (substantive), `v1-cosmetic.html` (ignored).

## HTTP (:8092)

| Surface | Path |
|---|---|
| Sources | `/sources`, `/api/sources` |
| Changes inbox | `/changes`, `/api/changes` |
| Change detail + impact | `/change?change_id=…` |
| Check source | `/api/regulatory/check?source_id=…` |
| Review | `/api/regulatory/review&status=ACCEPTED\|IGNORED` |
| FW suggestions | `/suggestions` |

Auth: `superuser=1` or `actor_tenants=…` (same engine gate as Phase 2–3).
Client impact rows are filtered by actor tenants (fail-closed if neither superuser nor actor set).

## Boundaries

- Never writes CISO `LoadedLibrary` / published FrameworkVersion.
- Client programs remain pinned; impact is advisory.
- Sources/Changes inbox is global KB-level (authenticated); client impact is tenant-scoped.
- AI semantic analysis deferred to Phase 5.

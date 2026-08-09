# UI — WayFold Compliance

## Principio

La superficie pubblica è **WayFold Compliance** (engine su produzione: `/`).

Design system definitivo: `docs/design/DESIGN-SYSTEM.md`  
Mockup: `docs/design/wayfold-compliance-definitive-mockup.html`

Nessun nome di vendor in titoli o copy rivolto all’utente.

## Lingua e tema

- Default: **italiano**
- Toggle **IT/EN** in sidebar footer (query `?lang=`)
- Content area sempre light; sidebar navy (nessun dark mode contenuto)

## Token

Vedi `engine/ui_shell.py` e `docs/design/DESIGN-SYSTEM.md`:

| Token | Valore |
|---|---|
| bg | `#f5f7fb` |
| surface | `#ffffff` |
| ink | `#151b2b` |
| muted | `#6f7a8e` |
| sidebar | `#101522` |
| primary | `#675cf2` |
| font | Inter / system-ui |

## Shell

```python
from engine.ui_shell import render_shell
from engine.i18n import t

html = render_shell(title, nav_qs, body, lang="it", active_path="/portfolio")
```

Nuove pagine: **sempre** `render_shell` + stringhe da `engine/i18n.py` + label stato da `engine/ui_labels.py` + icone da `engine/ui_icons.py`.

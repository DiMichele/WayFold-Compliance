"""Authoring forms and Knowledge Base workspace pages."""

from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import parse_qsl, urlencode

from engine.framework_registry import FRAMEWORK_TYPES
from engine.i18n import DEFAULT_LANG, normalize_lang, t, with_lang
from engine.ui_components import empty_state, mapping_badge, page_header, status_badge
from engine.ui_labels import framework_status_label, review_label
from engine.ui_shell import render_shell, table_wrap


def _lang(nav_qs: str) -> str:
    return normalize_lang(dict(parse_qsl(nav_qs)).get("lang", DEFAULT_LANG))


def _shell(title: str, nav_qs: str, body: str, *, lang: str, active: str, crumb: str) -> str:
    return render_shell(
        f"{title} — WayFold Compliance",
        with_lang(nav_qs, lang),
        body,
        lang=lang,
        active_path=active,
        breadcrumb=crumb,
    )


def _field(name: str, label: str, *, value: str = "", kind: str = "text", required: bool = False, options: list[tuple[str, str]] | None = None, full: bool = False, help_text: str = "") -> str:
    req = " required" if required else ""
    cls = "form-field full" if full else "form-field"
    help_html = f"<div class='client-meta'>{escape(help_text)}</div>" if help_text else ""
    if kind == "textarea":
        control = f"<textarea name='{escape(name)}'{req}>{escape(value)}</textarea>"
    elif kind == "select":
        opts = "".join(
            f"<option value='{escape(v)}' {'selected' if v == value else ''}>{escape(lbl)}</option>"
            for v, lbl in (options or [])
        )
        control = f"<select name='{escape(name)}'{req}>{opts}</select>"
    else:
        control = f"<input type='{escape(kind)}' name='{escape(name)}' value='{escape(value)}'{req}>"
    return f"<div class='{cls}'><label>{escape(label)}</label>{control}{help_html}</div>"


def framework_create_page(nav_qs: str, *, error: str = "") -> str:
    lang = _lang(nav_qs)
    opts = [(x, x) for x in FRAMEWORK_TYPES]
    form = f"""
<form method="post" action="/frameworks/new?{nav_qs}" class="panel" style="padding:18px">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <div class="form-grid">
    {_field("name", "Nome", required=True)}
    {_field("short_name", "Nome breve")}
    {_field("type", "Tipo", kind="select", value="Normativa", options=opts)}
    {_field("publisher", "Publisher")}
    {_field("jurisdiction", "Giurisdizione")}
    {_field("language", "Lingua", value="it")}
    {_field("official_url", "URL ufficiale", kind="url", full=True)}
    {_field("description", "Descrizione", kind="textarea", full=True)}
    {_field("version_label", "Prima versione (bozza)", value="1.0", required=True, full=True)}
  </div>
  <div class="page-actions" style="margin-top:16px">
    <button class="btn primary" type="submit">Crea framework</button>
    <a class="btn ghost" href="/frameworks?{nav_qs}">Annulla</a>
  </div>
</form>
"""
    body = page_header(
        eyebrow=t(lang, "nav.section.knowledge"),
        title="Nuovo framework / normativa",
        subtitle="Crea la scheda Knowledge Base e la prima versione in bozza.",
    ) + form
    return _shell("Nuovo framework", nav_qs, body, lang=lang, active="/frameworks", crumb="Nuovo framework")


def version_create_page(nav_qs: str, *, frameworks: list[Any], preselect: str = "", error: str = "") -> str:
    lang = _lang(nav_qs)
    opts = [("", "— seleziona —")] + [(f.id, f.name) for f in frameworks]
    form = f"""
<form method="post" action="/frameworks/versions/new?{nav_qs}" class="panel" style="padding:18px">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <div class="form-grid">
    {_field("framework_id", "Framework", kind="select", value=preselect, required=True, options=opts, full=True)}
    {_field("version", "Version label", required=True, value="1.0")}
    {_field("publication_date", "Data pubblicazione", kind="date")}
    {_field("effective_date", "Data efficacia", kind="date")}
    {_field("notes", "Note", kind="textarea", full=True)}
  </div>
  <p class="meta">La nuova versione viene creata in stato Bozza.</p>
  <div class="page-actions" style="margin-top:16px">
    <button class="btn primary" type="submit">Crea versione</button>
  </div>
</form>
"""
    body = page_header(eyebrow=t(lang, "fwkb.title"), title="Nuova versione framework", subtitle="") + form
    return _shell("Nuova versione", nav_qs, body, lang=lang, active="/frameworks", crumb="Nuova versione")


def requirement_create_page(
    nav_qs: str,
    *,
    versions: list[Any],
    preselect_version: str = "",
    error: str = "",
) -> str:
    lang = _lang(nav_qs)
    opts = [("", "— seleziona versione bozza —")] + [
        (v.id, f"{v.framework_name} @ {v.version} ({framework_status_label(lang, v.status)})")
        for v in versions
        if v.status == "DRAFT"
    ]
    type_opts = [
        ("Requisito", "Requisito"),
        ("Articolo", "Articolo"),
        ("Misura", "Misura"),
        ("Controllo normativo", "Controllo normativo"),
    ]
    form = f"""
<form method="post" action="/frameworks/requirements/new?{nav_qs}" class="panel" style="padding:18px">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <p class="meta">{escape(t(lang, 'req.term_help'))}</p>
  <div class="form-grid">
    {_field("version_id", "Versione framework", kind="select", value=preselect_version, required=True, options=opts, full=True)}
    {_field("code", "Codice", required=True)}
    {_field("title", "Titolo", required=True)}
    {_field("req_type", "Tipo", kind="select", options=type_opts)}
    {_field("section", "Sezione")}
    {_field("parent_code", "Parent (codice)")}
    {_field("order", "Ordine", kind="number", value="0")}
    {_field("source_reference", "Riferimento sorgente")}
    {_field("frequency", "Frequenza")}
    {_field("description", "Descrizione / testo", kind="textarea", full=True)}
    {_field("conditions", "Condizioni / note", kind="textarea", full=True)}
  </div>
  <div class="page-actions" style="margin-top:16px">
    <button class="btn primary" type="submit">Salva voce normativa</button>
  </div>
</form>
"""
    body = page_header(eyebrow=t(lang, "fwkb.requirements"), title="Nuova voce normativa", subtitle="") + form
    return _shell("Nuova voce normativa", nav_qs, body, lang=lang, active="/frameworks", crumb="Nuova voce normativa")


def control_create_page(nav_qs: str, *, prefill: dict[str, str] | None = None, error: str = "") -> str:
    lang = _lang(nav_qs)
    p = prefill or {}
    pri = [("HIGH", "Alta"), ("MEDIUM", "Media"), ("LOW", "Bassa"), ("CRITICAL", "Critica")]
    form = f"""
<form method="post" action="/controls/new?{nav_qs}" class="panel" style="padding:18px">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <div class="form-grid">
    {_field("code", "Codice", required=True, value=p.get("code", ""))}
    {_field("title", "Titolo", required=True, value=p.get("title", ""))}
    {_field("domain", "Dominio", value=p.get("domain", ""))}
    {_field("default_priority", "Priorità predefinita", kind="select", value=p.get("default_priority", "MEDIUM"), options=pri)}
    {_field("objective", "Obiettivo", kind="textarea", full=True, value=p.get("objective", ""))}
    {_field("description", "Descrizione", kind="textarea", full=True, value=p.get("description", ""))}
    {_field("implementation_guidance", "Indicazioni implementative", kind="textarea", full=True)}
    {_field("suggested_evidence", "Evidenze suggerite", kind="textarea", full=True)}
  </div>
  <p class="meta">Il controllo unificato non è legato a un singolo framework.</p>
  <div class="page-actions" style="margin-top:16px">
    <button class="btn primary" type="submit">Crea controllo</button>
    <a class="btn ghost" href="/controls?{nav_qs}">Annulla</a>
  </div>
</form>
"""
    body = page_header(eyebrow=t(lang, "catalog.title"), title="Nuovo controllo unificato", subtitle="") + form
    return _shell("Nuovo controllo", nav_qs, body, lang=lang, active="/controls", crumb="Nuovo controllo")


def control_catalog_page(
    controls: list[Any],
    nav_qs: str,
    *,
    usage: dict[str, dict[str, int]] | None = None,
) -> str:
    lang = _lang(nav_qs)
    usage = usage or {}
    if not controls:
        body = page_header(
            eyebrow=t(lang, "nav.section.knowledge"),
            title=t(lang, "catalog.title"),
            subtitle=t(lang, "catalog.meta"),
            actions_html=f"<a class='btn primary' href='/controls/new?{nav_qs}'>{escape(t(lang, 'catalog.new'))}</a>",
        ) + empty_state(title=t(lang, "catalog.empty_title"), body=t(lang, "catalog.empty_body"))
        return _shell(t(lang, "catalog.title"), nav_qs, body, lang=lang, active="/controls", crumb=t(lang, "catalog.title"))

    rows = []
    for c in controls:
        u = usage.get(c.code, {})
        rows.append(
            "<tr>"
            f"<td><code>{escape(c.code)}</code></td>"
            f"<td><a href='/controls/detail?control_id={escape(c.id)}&{nav_qs}'><strong>{escape(c.title)}</strong></a></td>"
            f"<td>{escape(c.domain or '—')}</td>"
            f"<td>{escape((c.description or '')[:120])}</td>"
            f"<td>{u.get('frameworks', 0)}</td>"
            f"<td>{u.get('requirements', 0)}</td>"
            f"<td>{escape(framework_status_label(lang, c.status) if c.status in {'DRAFT','PUBLISHED','RETIRED'} else t(lang, 'status.active') if c.status=='ACTIVE' else c.status)}</td>"
            f"<td><a class='btn sm' href='/controls/detail?control_id={escape(c.id)}&{nav_qs}'>Apri</a></td>"
            "</tr>"
        )
    table = f"""<table class="data-table"><thead><tr>
<th>Codice</th><th>Titolo</th><th>Dominio</th><th>Descrizione breve</th>
<th>Framework collegati</th><th>Requirement collegati</th><th>Stato</th><th></th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>"""
    body = (
        page_header(
            eyebrow=t(lang, "nav.section.knowledge"),
            title=t(lang, "catalog.title"),
            subtitle=t(lang, "catalog.meta"),
            actions_html=f"<a class='btn primary' href='/controls/new?{nav_qs}'>{escape(t(lang, 'catalog.new'))}</a>",
        )
        + f'<div class="panel">{table_wrap(table)}</div>'
    )
    return _shell(t(lang, "catalog.title"), nav_qs, body, lang=lang, active="/controls", crumb=t(lang, "catalog.title"))


def mapping_create_page(
    nav_qs: str,
    *,
    requirements: list[Any],
    controls: list[Any],
    prefill: dict[str, str] | None = None,
    error: str = "",
) -> str:
    lang = _lang(nav_qs)
    p = prefill or {}
    req_opts = [("", "—")] + [
        (
            r.id,
            f"{getattr(r, 'code', '')} — {getattr(r, 'title', '')} ({getattr(r, 'framework_name', '')} {getattr(r, 'framework_version', getattr(r, 'version', ''))})",
        )
        for r in requirements
    ]
    ctrl_opts = [("", "—")] + [(c.code, f"{c.code} — {c.title}") for c in controls]
    rel_opts = [("FULL", "Completa"), ("PARTIAL", "Parziale"), ("SUPPORTING", "Di supporto")]
    rev_opts = [
        ("DRAFT", "Bozza"),
        ("HUMAN_REVIEWED", "Da revisionare"),
        ("APPROVED", "Approvata"),
        ("REJECTED", "Rifiutata"),
    ]
    form = f"""
<form method="post" action="/mappings/new?{nav_qs}" class="panel" style="padding:18px" id="mapping-form">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <div class="form-grid">
    {_field("requirement_id", "Voce normativa / requisito", kind="select", value=p.get("requirement_id", ""), required=True, options=req_opts, full=True)}
    {_field("canonical_control_ref", "Controllo unificato", kind="select", value=p.get("canonical_control_ref", ""), required=True, options=ctrl_opts, full=True)}
    {_field("relation", "Relazione", kind="select", value=p.get("relation", "FULL"), options=rel_opts)}
    {_field("review_status", "Stato revisione", kind="select", value=p.get("review_status", "DRAFT"), options=rev_opts)}
    {_field("rationale", "Motivazione", kind="textarea", full=True, value=p.get("rationale", ""))}
    {_field("uncovered_delta", "Delta (obbligatorio se Parziale)", kind="textarea", full=True, value=p.get("uncovered_delta", ""), help_text="Obbligatorio per relazione Parziale.")}
  </div>
  <div class="page-actions" style="margin-top:16px">
    <button class="btn primary" type="submit">Salva mappatura</button>
    <a class="btn ghost" href="/mappings?{nav_qs}">Annulla</a>
  </div>
</form>
"""
    body = page_header(eyebrow=t(lang, "map.title"), title="Nuova mappatura", subtitle="") + form
    return _shell("Nuova mappatura", nav_qs, body, lang=lang, active="/mappings", crumb="Nuova mappatura")


def publish_page(nav_qs: str, *, version: Any, summary: dict[str, Any], error: str = "") -> str:
    lang = _lang(nav_qs)
    warn = ""
    if summary.get("unmapped", 0) > 0:
        warn = (
            f"<div class='mapping-delta'><strong>Attenzione:</strong> "
            f"{summary['unmapped']} requisiti non mappati. "
            f"Puoi pubblicare solo dopo conferma esplicita.</div>"
        )
    form = f"""
<div class="panel" style="padding:18px">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <h2>{escape(version.framework_name)} <code>{escape(version.version)}</code></h2>
  <div class="grid grid-4" style="margin:14px 0">
    <div class="metric"><div class="metric-label">Requirement totali</div><div class="metric-value">{summary.get('total_requirements', 0)}</div></div>
    <div class="metric"><div class="metric-label">Completi (FULL)</div><div class="metric-value">{summary.get('full', 0)}</div></div>
    <div class="metric"><div class="metric-label">Parziali</div><div class="metric-value">{summary.get('partial', 0)}</div></div>
    <div class="metric"><div class="metric-label">Di supporto</div><div class="metric-value">{summary.get('supporting', 0)}</div></div>
  </div>
  <p><strong>Non mappati:</strong> {summary.get('unmapped', 0)}</p>
  {warn}
  <form method="post" action="/frameworks/publish?{nav_qs}">
    <input type="hidden" name="version_id" value="{escape(version.id)}">
    <label style="display:flex;gap:8px;align-items:flex-start;margin:14px 0">
      <input type="checkbox" name="confirm" value="1" required>
      <span>{escape(t(lang, 'publish.confirm'))}</span>
    </label>
    <button class="btn primary" type="submit">{escape(t(lang, 'publish.title'))}</button>
    <a class="btn ghost" href="/frameworks/detail?framework_id={escape(version.framework_id)}&version_id={escape(version.id)}&{nav_qs}">Annulla</a>
  </form>
</div>
"""
    body = page_header(eyebrow=t(lang, "fwkb.title"), title=t(lang, "publish.title"), subtitle="") + form
    return _shell(t(lang, "publish.title"), nav_qs, body, lang=lang, active="/frameworks", crumb=t(lang, "publish.title"))


def client_create_page(nav_qs: str, *, error: str = "") -> str:
    lang = _lang(nav_qs)
    form = f"""
<form method="post" action="/clients/new?{nav_qs}" class="panel" style="padding:18px">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <div class="form-grid">
    {_field("name", "Nome", required=True)}
    {_field("code", "Codice")}
    {_field("contact", "Referente")}
    {_field("status", "Stato", kind="select", value="ACTIVE", options=[("ACTIVE", "Attivo"), ("INACTIVE", "Inattivo")])}
    {_field("description", "Descrizione", kind="textarea", full=True)}
  </div>
  <div class="page-actions" style="margin-top:16px">
    <button class="btn primary" type="submit">Crea cliente</button>
  </div>
</form>
"""
    body = page_header(eyebrow=t(lang, "clients.title"), title="Nuovo cliente", subtitle="") + form
    return _shell("Nuovo cliente", nav_qs, body, lang=lang, active="/clients", crumb="Nuovo cliente")


def program_create_page(
    nav_qs: str,
    *,
    clients: list[dict[str, str]],
    published_versions: list[Any],
    preselect_tenant: str = "",
    error: str = "",
    preview: dict[str, Any] | None = None,
) -> str:
    lang = _lang(nav_qs)
    client_opts = [("", "—")] + [(c["tenant_id"], c["tenant_name"]) for c in clients]
    checks = "".join(
        f"<label style='display:flex;gap:8px;margin:6px 0'>"
        f"<input type='checkbox' name='version_ids' value='{escape(v.id)}'>"
        f"<span><strong>{escape(v.framework_name)}</strong> <code>{escape(v.version)}</code>"
        f" · {escape(framework_status_label(lang, v.status))}</span></label>"
        for v in published_versions
    ) or "<p class='meta'>Nessuna versione pubblicata disponibile.</p>"
    preview_html = ""
    if preview:
        preview_html = (
            f"<div class='mapping-delta' style='margin:12px 0'>"
            f"<strong>Anteprima checklist unificata</strong><br>"
            f"{preview.get('requirements', 0)} requirement · "
            f"{preview.get('unified_controls', 0)} controlli unificati · "
            f"{preview.get('unmapped', 0)} unmapped"
            f"</div>"
        )
    form = f"""
<form method="post" action="/programs/new?{nav_qs}" class="panel" style="padding:18px">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <div class="form-grid">
    {_field("name", "Nome programma", required=True, full=True)}
    {_field("tenant_id", "Cliente", kind="select", value=preselect_tenant, required=True, options=client_opts, full=True)}
    {_field("scope", "Scope")}
    {_field("owner", "Responsabile")}
    {_field("status", "Stato", kind="select", value="ACTIVE", options=[("ACTIVE","Attivo"),("DRAFT","Bozza")])}
    {_field("description", "Descrizione", kind="textarea", full=True)}
  </div>
  <h3 style="margin:18px 0 8px">Seleziona framework (versioni pubblicate)</h3>
  <div class="panel" style="padding:12px;background:var(--wf-surface-2)">{checks}</div>
  {preview_html}
  <div class="page-actions" style="margin-top:16px">
    <button class="btn" type="submit" name="action" value="preview">Genera anteprima checklist</button>
    <button class="btn primary" type="submit" name="action" value="create">Crea programma</button>
  </div>
</form>
"""
    body = page_header(eyebrow=t(lang, "clients.title"), title="Nuovo programma", subtitle="") + form
    return _shell("Nuovo programma", nav_qs, body, lang=lang, active="/clients", crumb="Nuovo programma")


def csv_import_page(
    nav_qs: str,
    *,
    version_id: str,
    preview: dict[str, Any] | None = None,
    error: str = "",
) -> str:
    lang = _lang(nav_qs)
    preview_html = ""
    if preview:
        errs = preview.get("errors") or []
        preview_html = f"""
<div class="panel" style="padding:14px;margin-bottom:12px">
  <p><strong>Nuovi:</strong> {len(preview.get('new') or [])} ·
  <strong>Aggiornamenti:</strong> {len(preview.get('updates') or [])} ·
  <strong>Errori:</strong> {len(errs)}</p>
  {"<ul class='compact'>" + "".join(f"<li>{escape(str(e))}</li>" for e in errs[:20]) + "</ul>" if errs else "<p class='meta'>Validazione OK.</p>"}
</div>
"""
    form = f"""
<form method="post" action="/frameworks/requirements/import?{nav_qs}" class="panel" style="padding:18px">
  <input type="hidden" name="version_id" value="{escape(version_id)}">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <p><a class="btn sm" href="/api/frameworks/requirements/template.csv">Scarica template CSV</a></p>
  <div class="form-field full"><label>CSV</label>
  <textarea name="csv_text" required style="min-height:220px;font-family:var(--wf-mono)"></textarea></div>
  {preview_html}
  <div class="page-actions" style="margin-top:16px">
    <button class="btn" type="submit" name="action" value="preview">Anteprima / validazione</button>
    <button class="btn primary" type="submit" name="action" value="apply">Importa</button>
  </div>
</form>
"""
    body = page_header(eyebrow=t(lang, "fwkb.requirements"), title="Importa CSV", subtitle="") + form
    return _shell("Importa CSV", nav_qs, body, lang=lang, active="/frameworks", crumb="Importa CSV")


def control_edit_page(nav_qs: str, *, detail: Any, expected_version: int = 1, error: str = "") -> str:
    lang = _lang(nav_qs)
    status_opts = [
        ("IMPLEMENTED", "Implementato"),
        ("IN_PROGRESS", "In corso"),
        ("NOT_IMPLEMENTED", "Non implementato"),
        ("NOT_APPLICABLE", "Non applicabile"),
    ]
    pri = [("HIGH", "Alta"), ("MEDIUM", "Media"), ("LOW", "Bassa"), ("CRITICAL", "Critica")]
    form = f"""
<form method="post" action="/api/control/update?{nav_qs}" class="panel" style="padding:18px" enctype="application/x-www-form-urlencoded">
  <input type="hidden" name="control_id" value="{escape(detail.control_ref)}">
  <input type="hidden" name="expected_version" value="{expected_version}">
  {"<p class='badge danger'>" + escape(error) + "</p>" if error else ""}
  <div class="form-grid">
    {_field("status", "Stato", kind="select", value=str(getattr(detail.status, 'value', detail.status)), options=status_opts)}
    {_field("owner", "Responsabile", value=detail.owner or "")}
    {_field("due_date", "Scadenza", kind="date", value=(detail.due_date or "")[:10])}
    {_field("priority", "Priorità", kind="select", value=detail.priority or "MEDIUM", options=pri)}
    {_field("description", "Descrizione implementazione", kind="textarea", full=True, value=getattr(detail, 'description', '') or '')}
    {_field("not_applicable_rationale", "Motivazione N/A", kind="textarea", full=True, value=getattr(detail, 'not_applicable_rationale', '') or '', help_text="Obbligatoria se lo stato è Non applicabile.")}
  </div>
  <div class="page-actions" style="margin-top:16px">
    <button class="btn primary" type="submit">Salva</button>
    <a class="btn ghost" href="/control?control_ref={escape(detail.control_ref)}&{nav_qs}">Annulla</a>
  </div>
</form>
"""
    body = page_header(eyebrow="Controllo", title=f"Modifica {detail.name or detail.control_ref}", subtitle="") + form
    return _shell("Modifica controllo", nav_qs, body, lang=lang, active="/checklist", crumb="Modifica controllo")


__all__ = [
    "framework_create_page",
    "version_create_page",
    "requirement_create_page",
    "control_create_page",
    "control_catalog_page",
    "mapping_create_page",
    "publish_page",
    "client_create_page",
    "program_create_page",
    "csv_import_page",
    "control_edit_page",
]

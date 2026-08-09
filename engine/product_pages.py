"""Product completion pages: Frameworks KB, Mappings, Audit, Clients, Settings."""

from __future__ import annotations

from html import escape
from typing import Any
from urllib.parse import parse_qsl, urlencode

from engine.dates import format_display_datetime
from engine.gap_assessment import GAP_TAXONOMY_IT
from engine.i18n import DEFAULT_LANG, normalize_lang, t, with_lang
from engine.ui_components import empty_state, mapping_badge, page_header, status_badge
from engine.ui_labels import framework_status_label, review_label
from engine.ui_shell import render_shell, table_wrap


def _lang(nav_qs: str) -> str:
    return normalize_lang(dict(parse_qsl(nav_qs)).get("lang", DEFAULT_LANG))


def frameworks_page(
    versions: list[Any],
    usage: dict[str, int],
    nav_qs: str,
    *,
    meta_by_id: dict[str, Any] | None = None,
    coverage_by_fw: dict[str, str] | None = None,
) -> str:
    lang = _lang(nav_qs)
    nav_qs = with_lang(nav_qs, lang)
    meta_by_id = meta_by_id or {}
    coverage_by_fw = coverage_by_fw or {}
    actions = (
        f"<a class='btn primary' href='/frameworks/new?{nav_qs}'>{escape(t(lang, 'fwkb.new'))}</a>"
    )
    if not versions:
        body = page_header(
            eyebrow=t(lang, "nav.section.knowledge"),
            title=t(lang, "fwkb.title"),
            subtitle=t(lang, "fwkb.meta"),
            actions_html=actions,
        ) + empty_state(
            title=t(lang, "fwkb.empty_title"),
            body=t(lang, "fwkb.empty_body"),
        )
        return render_shell(
            f"{t(lang, 'fwkb.title')} — WayFold Compliance",
            nav_qs,
            body,
            lang=lang,
            active_path="/frameworks",
            breadcrumb=t(lang, "fwkb.title"),
        )

    groups: dict[str, list[Any]] = {}
    for v in versions:
        groups.setdefault(v.framework_id, []).append(v)

    rows = []
    for fw_id, vers in sorted(groups.items(), key=lambda x: x[1][0].framework_name):
        current = next((x for x in vers if x.status == "PUBLISHED"), vers[0])
        meta = meta_by_id.get(fw_id)
        fw_type = getattr(meta, "type", None) or "Framework"
        publisher = getattr(meta, "publisher", None) or current.publisher
        req_count = len(current.requirements)
        clients = usage.get(fw_id, 0)
        href = f"/frameworks/detail?framework_id={escape(fw_id)}&{nav_qs}"
        rows.append(
            "<tr>"
            f"<td><a href='{href}'><strong>{escape(current.framework_name)}</strong></a></td>"
            f"<td>{escape(fw_type)}</td>"
            f"<td>{escape(publisher)}</td>"
            f"<td><code>{escape(current.version)}</code></td>"
            f"<td>{escape(framework_status_label(lang, current.status))}</td>"
            f"<td>{req_count}</td>"
            f"<td>{escape(coverage_by_fw.get(fw_id, '—'))}</td>"
            f"<td>{clients}</td>"
            f"<td><a class='btn sm' href='{href}'>{escape(t(lang, 'action.open'))}</a></td>"
            "</tr>"
        )
    table = f"""<table class="data-table"><thead><tr>
<th>Nome</th><th>{escape(t(lang, 'fwkb.type'))}</th><th>{escape(t(lang, 'fwkb.publisher'))}</th>
<th>{escape(t(lang, 'fwkb.current_version'))}</th><th>{escape(t(lang, 'col.status'))}</th>
<th>{escape(t(lang, 'col.requirements'))}</th><th>{escape(t(lang, 'fwkb.coverage'))}</th>
<th>{escape(t(lang, 'fwkb.clients_using'))}</th><th></th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>"""
    body = (
        page_header(
            eyebrow=t(lang, "nav.section.knowledge"),
            title=t(lang, "fwkb.title"),
            subtitle=t(lang, "fwkb.meta"),
            actions_html=actions,
        )
        + f'<div class="panel">{table_wrap(table)}</div>'
    )
    return render_shell(
        f"{t(lang, 'fwkb.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/frameworks",
        breadcrumb=t(lang, "fwkb.title"),
    )


def framework_detail_page(
    versions: list[Any],
    *,
    selected_id: str | None,
    nav_qs: str,
    usage_clients: list[str] | None = None,
    tab: str = "overview",
    meta: Any | None = None,
    mappings: list[Any] | None = None,
    coverage: dict[str, Any] | None = None,
) -> str:
    lang = _lang(nav_qs)
    nav_qs = with_lang(nav_qs, lang)
    if not versions:
        return frameworks_page([], {}, nav_qs)
    selected = next((v for v in versions if v.id == selected_id), versions[0])
    tab = tab or "overview"
    base = f"/frameworks/detail?framework_id={escape(selected.framework_id)}&version_id={escape(selected.id)}&{nav_qs}"
    tabs = [
        ("overview", "Panoramica"),
        ("versions", "Versioni"),
        ("requirements", "Requisiti"),
        ("mappings", "Mappature"),
        ("sources", "Fonti"),
        ("usage", "Utilizzo"),
    ]
    tabs_html = (
        '<div class="tabs">'
        + "".join(
            f"<a class='{'active' if tab == key else ''}' href='{base}&tab={key}'>{escape(label)}</a>"
            for key, label in tabs
        )
        + "</div>"
    )
    is_draft = selected.status == "DRAFT"
    actions = (
        f"<a class='btn' href='/frameworks/versions/new?framework_id={escape(selected.framework_id)}&{nav_qs}'>+ Nuova versione</a>"
        f"<a class='btn' href='/api/frameworks/clone?version_id={escape(selected.id)}&new_version={escape(selected.version)}.1&{nav_qs}'>Clona come nuova bozza</a>"
    )
    if is_draft:
        actions += (
            f"<a class='btn' href='/frameworks/requirements/new?version_id={escape(selected.id)}&{nav_qs}'>{escape(t(lang, 'req.new'))}</a>"
            f"<a class='btn' href='/frameworks/requirements/import?version_id={escape(selected.id)}&{nav_qs}'>{escape(t(lang, 'req.import_csv'))}</a>"
            f"<a class='btn primary' href='/frameworks/publish?version_id={escape(selected.id)}&{nav_qs}'>{escape(t(lang, 'publish.title'))}</a>"
        )

    ver_rows = "".join(
        "<tr>"
        f"<td><a href='/frameworks/detail?framework_id={escape(selected.framework_id)}"
        f"&version_id={escape(v.id)}&tab=versions&{nav_qs}'><code>{escape(v.version)}</code></a></td>"
        f"<td>{escape(framework_status_label(lang, v.status))}</td>"
        f"<td>{len(v.requirements)}</td>"
        f"<td>{escape(format_display_datetime(v.published_at or v.created_at, lang=lang))}</td>"
        "</tr>"
        for v in versions
    )
    code_to_depth: dict[str, int] = {}
    for r in selected.requirements:
        parent = getattr(r, "parent_id", None)
        depth = 0
        if parent:
            parent_code = next((x.code for x in selected.requirements if x.id == parent), "")
            depth = parent_code.count(".") + (1 if parent_code else r.code.count("."))
        else:
            depth = r.code.count(".")
        code_to_depth[r.code] = depth
    req_rows = []
    for r in sorted(selected.requirements, key=lambda x: (x.order, x.code)):
        depth = code_to_depth.get(r.code, 0)
        pad = "&nbsp;" * (depth * 4)
        req_rows.append(
            "<tr>"
            f"<td>{pad}<code>{escape(r.code)}</code></td>"
            f"<td>{escape(r.title)}</td>"
            f"<td>{escape(getattr(r, 'req_type', '') or '—')}</td>"
            f"<td>{escape(r.section or '—')}</td>"
            f"<td>{'Foglia' if getattr(r, 'is_leaf', True) else 'Nodo'}</td>"
            "</tr>"
        )
    clients = "".join(f"<li>{escape(c)}</li>" for c in (usage_clients or [])) or (
        f"<li>{escape(t(lang, 'client.none'))}</li>"
    )
    map_rows = "".join(
        "<tr>"
        f"<td><code>{escape(m.requirement_code)}</code></td>"
        f"<td><code>{escape(m.canonical_control_ref)}</code></td>"
        f"<td>{mapping_badge(lang, m.relation.value if hasattr(m.relation, 'value') else m.relation)}</td>"
        f"<td>{escape(m.uncovered_delta or '—')}</td>"
        f"<td>{escape(review_label(lang, m.review_status))}</td>"
        "</tr>"
        for m in (mappings or [])
        if m.framework_version == selected.version
    )
    cov = coverage or {}
    overview = f"""
<div class="panel" style="padding:16px">
  <div class="detail-grid">
    <div class="field"><label>Publisher</label><div class="field-value">{escape(selected.publisher)}</div></div>
    <div class="field"><label>Tipo</label><div class="field-value">{escape(getattr(meta, 'type', 'Framework') if meta else 'Framework')}</div></div>
    <div class="field"><label>Versione</label><div class="field-value"><code>{escape(selected.version)}</code></div></div>
    <div class="field"><label>Stato</label><div class="field-value">{escape(framework_status_label(lang, selected.status))}</div></div>
    <div class="field"><label>Requirement</label><div class="field-value">{len(selected.requirements)}</div></div>
    <div class="field"><label>Copertura</label><div class="field-value">{cov.get('mapped', 0)}/{cov.get('total_requirements', 0)} mappati · {cov.get('unmapped', 0)} non mappati</div></div>
  </div>
  <p class="meta" style="margin-top:12px">{escape(getattr(meta, 'description', '') or selected.notes or '')}</p>
  <p class="client-meta">{escape(t(lang, 'req.term_help'))}</p>
</div>
"""
    panels = {
        "overview": overview,
        "versions": f"<div class='panel'><h2>{escape(t(lang, 'fwkb.versions'))}</h2>{table_wrap(f"<table class='data-table'><thead><tr><th>Versione</th><th>Stato</th><th>Requirement</th><th>Data</th></tr></thead><tbody>{ver_rows}</tbody></table>")}</div>",
        "requirements": f"<div class='panel'><h2>{escape(t(lang, 'fwkb.requirements'))}</h2>{table_wrap(f"<table class='data-table'><thead><tr><th>Codice</th><th>Titolo</th><th>Tipo</th><th>Sezione</th><th></th></tr></thead><tbody>{''.join(req_rows) or '<tr><td colspan=5>Nessuna voce normativa. Aggiungi manualmente o importa CSV.</td></tr>'}</tbody></table>")}</div>",
        "mappings": f"<div class='panel'><h2>Mappature</h2><p><a class='btn sm primary' href='/mappings/new?framework_id={escape(selected.framework_id)}&version_id={escape(selected.id)}&{nav_qs}'>{escape(t(lang,'map.new'))}</a></p>{table_wrap(f"<table class='data-table'><thead><tr><th>Requisito</th><th>Controllo</th><th>Relazione</th><th>Delta</th><th>Stato</th></tr></thead><tbody>{map_rows or '<tr><td colspan=5>—</td></tr>'}</tbody></table>")}</div>",
        "sources": f"<div class='panel'><h2>Fonti</h2><p class='meta'>URL ufficiale: {escape(getattr(meta, 'official_url', '') or selected.source_url or '—')}</p><p><a class='btn sm' href='/changes?{nav_qs}'>Apri Intelligence normativa</a></p></div>",
        "usage": f"<div class='panel'><h2>{escape(t(lang, 'fwkb.usage'))}</h2><ul class='compact'>{clients}</ul></div>",
    }
    body = (
        page_header(
            eyebrow=t(lang, "fwkb.title"),
            title=selected.framework_name,
            subtitle=f"{selected.publisher} · {selected.version} · {framework_status_label(lang, selected.status)}",
            actions_html=actions,
        )
        + tabs_html
        + panels.get(tab, overview)
    )
    return render_shell(
        f"{selected.framework_name} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/frameworks",
        breadcrumb=selected.framework_name,
    )


def mappings_page(
    mappings: list[Any],
    unmapped: list[Any],
    nav_qs: str,
    *,
    filters: dict[str, str] | None = None,
) -> str:
    lang = _lang(nav_qs)
    nav_qs = with_lang(nav_qs, lang)
    filters = filters or {}
    rows = []
    for m in mappings:
        rel = m.relation.value if hasattr(m.relation, "value") else m.relation
        rev = m.review_status.value if hasattr(m.review_status, "value") else m.review_status
        tip = f'title="{escape(rel)}"'
        rows.append(
            "<tr>"
            f"<td><code>{escape(m.requirement_code)}</code></td>"
            f"<td>{escape(m.framework_name)} <code>{escape(m.framework_version)}</code></td>"
            f"<td><code>{escape(m.canonical_control_ref)}</code></td>"
            f"<td {tip}>{mapping_badge(lang, rel)}</td>"
            f"<td>{escape(m.uncovered_delta or '—')}</td>"
            f"<td>{escape(m.rationale or '—')}</td>"
            f"<td>{escape(review_label(lang, rev))}</td>"
            f"<td><a class='btn sm' href='/mappings/new?requirement_id={escape(m.requirement_id)}&{nav_qs}'>Modifica</a></td>"
            "</tr>"
        )
    unmapped_rows = "".join(
        "<tr>"
        f"<td><code>{escape(u.code)}</code></td>"
        f"<td>{escape(u.framework_name)} <code>{escape(u.framework_version)}</code></td>"
        f"<td>{escape(u.title)}</td>"
        f"<td style='white-space:nowrap'>"
        f"<a class='btn sm' href='/mappings/new?requirement_id={escape(u.id)}&{nav_qs}'>{escape(t(lang, 'map.associate'))}</a> "
        f"<a class='btn sm' href='/controls/new?from_requirement={escape(u.id)}&title={escape(u.title)}&{nav_qs}'>{escape(t(lang, 'map.create_control'))}</a>"
        f"</td>"
        "</tr>"
        for u in unmapped
    )
    form = f"""
<form class="filter-bar" method="get" action="/mappings">
  <input type="hidden" name="program_id" value="{escape(filters.get('program_id',''))}">
  <input type="hidden" name="lang" value="{escape(lang)}">
  <label>Relazione
    <select name="relation">
      <option value="">—</option>
      <option value="FULL" {"selected" if filters.get("relation")=="FULL" else ""}>Completa</option>
      <option value="PARTIAL" {"selected" if filters.get("relation")=="PARTIAL" else ""}>Parziale</option>
      <option value="SUPPORTING" {"selected" if filters.get("relation")=="SUPPORTING" else ""}>Di supporto</option>
    </select>
  </label>
  <label>Stato
    <select name="review">
      <option value="">—</option>
      <option value="DRAFT" {"selected" if filters.get("review")=="DRAFT" else ""}>Bozza</option>
      <option value="HUMAN_REVIEWED" {"selected" if filters.get("review")=="HUMAN_REVIEWED" else ""}>Da revisionare</option>
      <option value="APPROVED" {"selected" if filters.get("review")=="APPROVED" else ""}>Approvata</option>
      <option value="REJECTED" {"selected" if filters.get("review")=="REJECTED" else ""}>Rifiutata</option>
    </select>
  </label>
  <label><input type="checkbox" name="unmapped_only" value="1" {"checked" if filters.get("unmapped_only")=="1" else ""}> Solo non mappati</label>
  <button class="btn primary sm" type="submit">{escape(t(lang, 'gaps.filter'))}</button>
</form>
"""
    table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.requirement'))}</th>
<th>{escape(t(lang,'col.framework'))}</th>
<th>{escape(t(lang,'col.control'))}</th>
<th>{escape(t(lang,'col.mapping'))}</th>
<th>{escape(t(lang,'col.delta'))}</th>
<th>{escape(t(lang,'col.rationale'))}</th>
<th>{escape(t(lang,'col.status'))}</th>
<th></th>
</tr></thead><tbody>{''.join(rows) or f"<tr><td colspan='8'>{escape(t(lang,'map.empty'))}</td></tr>"}</tbody></table>"""
    um_table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.requirement'))}</th><th>{escape(t(lang,'col.framework'))}</th>
<th>{escape(t(lang,'col.title'))}</th><th></th></tr></thead>
<tbody>{unmapped_rows or f"<tr><td colspan='4'>{escape(t(lang,'map.unmapped_empty'))}</td></tr>"}</tbody></table>"""
    body = (
        page_header(
            eyebrow=t(lang, "nav.section.knowledge"),
            title=t(lang, "map.title"),
            subtitle=t(lang, "map.meta"),
            actions_html=f"<a class='btn primary' href='/mappings/new?{nav_qs}'>{escape(t(lang, 'map.new'))}</a>",
        )
        + form
        + f'<div class="panel">{table_wrap(table)}</div>'
        + f"<section style='margin-top:16px'><h2>{escape(t(lang,'map.unmapped'))}</h2>"
        + f'<div class="panel">{table_wrap(um_table)}</div></section>'
    )
    return render_shell(
        f"{t(lang, 'map.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/mappings",
        breadcrumb=t(lang, "map.title"),
    )


def audit_page(events: list[Any], nav_qs: str, *, filters: dict[str, str] | None = None) -> str:
    lang = _lang(nav_qs)
    nav_qs = with_lang(nav_qs, lang)
    filters = filters or {}
    rows = []
    for ev in events:
        detail = ev.detail or ""
        if ev.old_value or ev.new_value:
            detail = (
                f"{detail} "
                f"old={escape(str(ev.old_value or {}))} → new={escape(str(ev.new_value or {}))}"
            ).strip()
        rows.append(
            "<tr>"
            f"<td>{escape(format_display_datetime(ev.timestamp, lang=lang))}</td>"
            f"<td>{escape(ev.actor_user_id)}</td>"
            f"<td><code>{escape(ev.action)}</code></td>"
            f"<td>{escape(ev.entity_type)} <code>{escape(ev.entity_id)}</code></td>"
            f"<td>{escape(ev.tenant_id or '—')}</td>"
            f"<td class='client-meta'>{detail or '—'}</td>"
            "</tr>"
        )
    form = f"""
<form class="filter-bar" method="get" action="/audit">
  <input type="hidden" name="lang" value="{escape(lang)}">
  <label>Cliente <input name="tenant_id" value="{escape(filters.get('tenant_id',''))}"></label>
  <label>Utente <input name="actor" value="{escape(filters.get('actor',''))}"></label>
  <label>Azione <input name="action" value="{escape(filters.get('action',''))}"></label>
  <label>Da <input name="date_from" type="date" value="{escape(filters.get('date_from',''))}"></label>
  <label>A <input name="date_to" type="date" value="{escape(filters.get('date_to',''))}"></label>
  <button class="btn primary sm" type="submit">{escape(t(lang, 'gaps.filter'))}</button>
</form>
"""
    table = f"""<table class="data-table"><thead><tr>
<th>Data</th><th>Utente</th><th>Azione</th><th>Entità</th><th>Client</th><th>Dettaglio</th>
</tr></thead><tbody>{''.join(rows) or f"<tr><td colspan='6'>{escape(t(lang,'audit.empty'))}</td></tr>"}</tbody></table>"""
    body = (
        page_header(
            eyebrow=t(lang, "nav.section.admin"),
            title=t(lang, "audit.title"),
            subtitle=t(lang, "audit.meta"),
        )
        + form
        + f'<div class="panel">{table_wrap(table)}</div>'
    )
    return render_shell(
        f"{t(lang, 'audit.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/audit",
        breadcrumb=t(lang, "audit.title"),
    )


def clients_page(
    rows: list[Any],
    assignments: dict[str, list[str]],
    nav_qs: str,
    *,
    q: str = "",
    status: str = "",
    framework: str = "",
) -> str:
    lang = _lang(nav_qs)
    nav_qs = with_lang(nav_qs, lang)
    tenant_consultants: dict[str, list[str]] = {}
    for user, tenants in assignments.items():
        for tid in tenants:
            tenant_consultants.setdefault(tid, []).append(user)

    filtered = list(rows)
    if q:
        needle = q.lower()
        filtered = [
            r
            for r in filtered
            if needle in r.tenant_name.lower() or needle in r.program_name.lower()
        ]
    if status:
        filtered = [
            r
            for r in filtered
            if (getattr(r, "program_status", "ACTIVE") or "ACTIVE").upper() == status.upper()
        ]
    if framework:
        filtered = [r for r in filtered if any(framework.lower() in f.lower() for f in r.frameworks)]

    body_rows = []
    for r in filtered:
        consultants = ", ".join(tenant_consultants.get(r.tenant_id, [])) or "—"
        qs = urlencode(
            {
                **dict(parse_qsl(nav_qs)),
                "program_id": r.program_id,
                "tenant_name": r.tenant_name,
                "program_name": r.program_name,
            }
        )
        href = f"/client?{qs}"
        st = getattr(r, "program_status", "ACTIVE") or "ACTIVE"
        st_label = t(lang, "status.active") if st == "ACTIVE" else st
        body_rows.append(
            "<tr>"
            f"<td><a href='{href}'><strong>{escape(r.tenant_name)}</strong></a></td>"
            f"<td>{escape(r.program_name)}</td>"
            f"<td>{escape(', '.join(r.frameworks))}</td>"
            f"<td>{escape(consultants)}</td>"
            f"<td>{escape(st_label)}</td>"
            f"<td><a class='btn sm primary' href='{href}'>{escape(t(lang,'action.open'))}</a></td>"
            "</tr>"
        )
    filter_bar = f"""
<form class="filter-bar" method="get" action="/clients">
  <input type="hidden" name="lang" value="{escape(lang)}">
  <label>Ricerca <input name="q" value="{escape(q)}" placeholder="Cliente o programma"></label>
  <label>Stato
    <select name="status">
      <option value="">—</option>
      <option value="ACTIVE" {"selected" if status=="ACTIVE" else ""}>Attivo</option>
      <option value="DRAFT" {"selected" if status=="DRAFT" else ""}>Bozza</option>
    </select>
  </label>
  <label>Framework <input name="framework" value="{escape(framework)}"></label>
  <button class="btn primary sm" type="submit">Filtra</button>
</form>
"""
    table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.client'))}</th>
<th>{escape(t(lang,'col.program'))}</th>
<th>{escape(t(lang,'col.framework'))}</th>
<th>{escape(t(lang,'clients.consultant'))}</th>
<th>{escape(t(lang,'col.status'))}</th>
<th></th>
</tr></thead><tbody>{''.join(body_rows) or f"<tr><td colspan='6'>{escape(t(lang,'clients.empty'))}</td></tr>"}</tbody></table>"""
    body = (
        page_header(
            eyebrow=t(lang, "nav.section.workspace"),
            title=t(lang, "clients.title"),
            subtitle=t(lang, "clients.meta"),
            actions_html=(
                f"<a class='btn primary' href='/clients/new?{nav_qs}'>{escape(t(lang, 'clients.new'))}</a>"
                f"<a class='btn' href='/programs/new?{nav_qs}'>{escape(t(lang, 'program.new'))}</a>"
            ),
        )
        + filter_bar
        + f'<div class="panel">{table_wrap(table)}</div>'
    )
    return render_shell(
        f"{t(lang, 'clients.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/clients",
        breadcrumb=t(lang, "clients.title"),
    )


def settings_page(
    *,
    nav_qs: str,
    ai_settings: Any | None = None,
    users: list[Any] | None = None,
    assignments: dict[str, list[str]] | None = None,
    mfa_status: dict[str, Any] | None = None,
) -> str:
    lang = _lang(nav_qs)
    nav_qs = with_lang(nav_qs, lang)
    ai_block = ""
    if ai_settings is not None:
        enabled = bool(getattr(ai_settings, "ai_processing_enabled", False))
        ai_block = f"""
<section class="panel" style="margin-bottom:14px">
  <h2>{escape(t(lang, 'settings.ai'))}</h2>
  <p><strong>{escape(t(lang, 'settings.ai_status'))}:</strong>
  {"Abilitata" if enabled else "Disabilitata"}</p>
  <p class="client-meta">{escape(t(lang, 'settings.ai_note'))}</p>
  <p><a class="btn sm" href="/ai/settings?tenant_id={escape(getattr(ai_settings,'tenant_id',''))}&{nav_qs}">
  {escape(t(lang, 'action.open'))}</a></p>
</section>
"""
    user_rows = "".join(
        "<tr>"
        f"<td>{escape(u.username)}</td>"
        f"<td>{escape(u.role)}</td>"
        f"<td>{escape(', '.join(u.tenant_ids) or '—')}</td>"
        f"<td>{'MFA' if u.mfa_enabled else '—'}</td>"
        "</tr>"
        for u in (users or [])
    )
    assign_rows = "".join(
        f"<tr><td>{escape(u)}</td><td>{escape(', '.join(tids))}</td></tr>"
        for u, tids in sorted((assignments or {}).items())
    )
    mfa = mfa_status or {}
    body = f"""
{page_header(
    eyebrow=t(lang, 'nav.section.admin'),
    title=t(lang, 'settings.title'),
    subtitle=t(lang, 'settings.meta'),
)}
<section class="panel" style="margin-bottom:14px">
  <h2>{escape(t(lang, 'settings.general'))}</h2>
  <p class="client-meta">WayFold Compliance · sessione cookie HttpOnly · timeout inattività 45 minuti</p>
</section>
<section class="panel" style="margin-bottom:14px">
  <h2>{escape(t(lang, 'settings.users'))}</h2>
  {table_wrap(f"<table class='data-table'><thead><tr><th>Utente</th><th>Ruolo</th><th>Tenant</th><th>MFA</th></tr></thead><tbody>{user_rows or '<tr><td colspan=4>—</td></tr>'}</tbody></table>")}
</section>
<section class="panel" style="margin-bottom:14px">
  <h2>{escape(t(lang, 'settings.assignments'))}</h2>
  {table_wrap(f"<table class='data-table'><thead><tr><th>Consulente</th><th>Clienti</th></tr></thead><tbody>{assign_rows or '<tr><td colspan=2>—</td></tr>'}</tbody></table>")}
</section>
<section class="panel" style="margin-bottom:14px">
  <h2>{escape(t(lang, 'settings.evidence'))}</h2>
  <p class="client-meta">{escape(t(lang, 'settings.evidence_note'))}</p>
</section>
{ai_block}
<section class="panel">
  <h2>{escape(t(lang, 'settings.security'))}</h2>
  <p>MFA SUPER_ADMIN/CONSULTANT: {"abilitata in directory utenti" if mfa.get("supported") else "hook pronto"}</p>
  <p class="client-meta">Credenziale review temporanea: TEMPORARY REVIEW CREDENTIAL (solo audit esterno).</p>
</section>
"""
    return render_shell(
        f"{t(lang, 'settings.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/settings",
        breadcrumb=t(lang, "settings.title"),
    )


def gap_taxonomy_label(code: str) -> str:
    return GAP_TAXONOMY_IT.get(code, code)

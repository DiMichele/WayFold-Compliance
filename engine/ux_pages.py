"""Dense consultant HTML pages — WayFold Compliance design system + i18n."""

from __future__ import annotations

from html import escape
from urllib.parse import parse_qsl, urlencode

from engine.dates import format_display_date, is_overdue
from engine.i18n import DEFAULT_LANG, lang_from_qs, normalize_lang, t, with_lang
from engine.ui_components import (
    client_initials,
    empty_state,
    framework_chips,
    mapping_badge,
    metric_card,
    page_header,
    priority_badge,
    progress_bar,
    row_action,
    status_badge,
)
from engine.ui_labels import format_number, format_percent, status_label
from engine.ui_shell import render_shell, table_wrap


def _with_program(nav_qs: str, program_id: str) -> str:
    data = dict(parse_qsl(nav_qs, keep_blank_values=False))
    data["program_id"] = program_id
    return urlencode(data)


def _with_control(nav_qs: str, control_ref: str) -> str:
    data = dict(parse_qsl(nav_qs, keep_blank_values=False))
    data["control_ref"] = control_ref
    return urlencode(data)


def _lang(nav_qs: str, lang: str | None = None) -> str:
    if lang:
        return normalize_lang(lang)
    return normalize_lang(dict(parse_qsl(nav_qs)).get("lang", DEFAULT_LANG))


def _shell(
    title: str,
    nav_qs: str,
    body: str,
    *,
    lang: str,
    active_path: str,
    breadcrumb: str | None = None,
) -> str:
    return render_shell(
        title,
        with_lang(nav_qs, lang),
        body,
        lang=lang,
        active_path=active_path,
        breadcrumb=breadcrumb or title.split(" — ")[0],
    )


def portfolio_page(rows, nav_qs: str, lang: str | None = None) -> str:
    lang = _lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    clients = len({r.tenant_id for r in rows})
    gaps = sum(r.critical_gaps + r.high_priority_open for r in rows)
    overdue = sum(r.overdue_tasks for r in rows)
    unmapped = sum(r.unmapped for r in rows)

    body_rows = []
    for r in rows:
        ready = format_percent(r.implementation_readiness, lang=lang)
        ratio = r.implementation_readiness
        client_qs = _with_program(nav_qs, r.program_id)
        href = f"/client?{client_qs}"
        body_rows.append(
            "<tr>"
            f"<td><div class='client-cell'>"
            f"<div class='client-logo' aria-hidden='true'>{escape(client_initials(r.tenant_name))}</div>"
            f"<div><div class='client-name'><a href='{href}'>{escape(r.tenant_name)}</a></div>"
            f"<div class='client-meta'>{escape(r.program_name)}</div></div></div></td>"
            f"<td>{framework_chips(r.frameworks)}</td>"
            f"<td><div class='readiness-cell'><strong>{escape(ready)}</strong>"
            f"{progress_bar(ratio)}</div></td>"
            f"<td>{format_number(r.critical_gaps, lang=lang)}</td>"
            f"<td>{format_number(r.overdue_tasks, lang=lang)}</td>"
            f"<td>{escape(format_display_date(r.next_deadline, lang=lang))}</td>"
            f"<td>{row_action(href, label=t(lang,'action.open'))}</td>"
            "</tr>"
        )

    table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.client'))}</th>
<th>{escape(t(lang,'col.framework'))}</th>
<th>{escape(t(lang,'col.readiness'))}</th>
<th>{escape(t(lang,'col.critical_gaps'))}</th>
<th>{escape(t(lang,'col.overdue'))}</th>
<th>{escape(t(lang,'col.next_deadline'))}</th>
<th></th>
</tr></thead><tbody>{''.join(body_rows) or f'<tr><td colspan="7">{escape(t(lang,"portfolio.empty"))}</td></tr>'}</tbody></table>"""

    if not rows:
        steps = "".join(
            f"<li><strong>{i}.</strong> {escape(t(lang, key))}</li>"
            for i, key in enumerate(
                (
                    "onboarding.step1",
                    "onboarding.step2",
                    "onboarding.step3",
                    "onboarding.step4",
                ),
                start=1,
            )
        )
        body = f"""
{page_header(eyebrow=t(lang,'portfolio.eyebrow'), title=t(lang,'onboarding.title'), subtitle=t(lang,'onboarding.meta'))}
<div class="panel">
  <div class="panel-body">
    <ol class="compact" style="margin:0 0 16px 1.2rem;line-height:1.7">{steps}</ol>
    <p class="meta">{escape(t(lang,'onboarding.note'))}</p>
    <p class="meta">{escape(t(lang,'onboarding.cta_hint'))}</p>
    <div class="page-actions" style="margin-top:16px">
      <a class="btn primary" href="/changes?{nav_qs}">{escape(t(lang,'onboarding.cta_primary'))}</a>
      <a class="btn" href="/sources?{nav_qs}">{escape(t(lang,'onboarding.cta_secondary'))}</a>
    </div>
  </div>
</div>
"""
        return _shell(
            f"{t(lang,'portfolio.title')} — WayFold Compliance",
            nav_qs,
            body,
            lang=lang,
            active_path="/portfolio",
            breadcrumb=t(lang, "portfolio.title"),
        )

    metrics = f"""
<div class="grid grid-4" style="margin-bottom:14px">
{metric_card(label=t(lang,'portfolio.metric.clients'), value=format_number(clients, lang=lang), icon_name='building')}
{metric_card(label=t(lang,'portfolio.metric.gaps'), value=format_number(gaps, lang=lang), icon_name='gap', tone='warning' if gaps else '')}
{metric_card(label=t(lang,'portfolio.metric.overdue'), value=format_number(overdue, lang=lang), icon_name='clock', tone='danger' if overdue else '')}
{metric_card(label=t(lang,'portfolio.metric.unmapped'), value=format_number(unmapped, lang=lang), icon_name='network')}
</div>"""

    def _action_row(title: str, count: int, desc: str, href: str, icon_name: str = "gap") -> str:
        return (
            f"<div class='action-row' style='display:flex;align-items:center;gap:14px;padding:12px 0;border-bottom:1px solid var(--wf-border)'>"
            f"<div style='font-size:22px;font-weight:800;min-width:42px'>{count}</div>"
            f"<div style='flex:1'><div style='font-weight:700'>{escape(title)}</div>"
            f"<div class='client-meta'>{escape(desc)}</div></div>"
            f"<a class='btn sm' href='{href}'>Apri</a></div>"
        )

    action_rows = []
    if unmapped:
        action_rows.append(
            _action_row(
                f"{unmapped} requisiti non mappati",
                unmapped,
                "Completare la copertura nella Knowledge Base o nel programma.",
                f"/gaps?mapped=0&{nav_qs}",
            )
        )
    if overdue:
        action_rows.append(
            _action_row(
                f"{overdue} attività scadute",
                overdue,
                "Attività oltre deadline su programmi autorizzati.",
                f"/tasks?{nav_qs}",
                "clock",
            )
        )
    if gaps:
        action_rows.append(
            _action_row(
                f"{gaps} gap critici / alta priorità",
                gaps,
                "Implementazioni incomplete o finding aperti.",
                f"/gaps?{nav_qs}",
            )
        )
    action_rows.append(
        _action_row(
            "Modifiche normative",
            0,
            "Revisionare l'inbox di intelligence normativa.",
            f"/changes?{nav_qs}",
            "radar",
        )
    )

    body = f"""
{page_header(eyebrow=t(lang,'portfolio.eyebrow'), title=t(lang,'portfolio.title'), subtitle=t(lang,'portfolio.meta'))}
{metrics}
<div class="panel" style="margin-bottom:14px">
  <div class="panel-head"><div class="panel-title">{escape(t(lang,'portfolio.action_center'))}</div>
  <div class="client-meta">{escape(t(lang,'portfolio.action_meta'))}</div></div>
  <div class="panel-body">{''.join(action_rows) or '<p class="meta">Nessuna azione urgente.</p>'}</div>
</div>
<div class="panel">
  <div class="panel-head"><div class="panel-title">{escape(t(lang,'portfolio.table'))}</div></div>
  {table_wrap(table)}
</div>
"""
    return _shell(
        f"{t(lang,'portfolio.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/portfolio",
        breadcrumb=t(lang, "portfolio.title"),
    )


def client_page(dash, nav_qs: str, lang: str | None = None) -> str:
    lang = _lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)

    fw_cards = []
    for f in dash.frameworks:
        ready_row = next(
            (r for r in dash.readiness if r["framework_name"] == f["framework_name"]),
            None,
        )
        fully = ready_row["fully_covered"] if ready_row else 0
        partial = ready_row["partially_covered"] if ready_row else 0
        unmapped = ready_row["unmapped"] if ready_row else 0
        ratio = ready_row["implementation_readiness"] if ready_row else None
        fw_cards.append(
            f"""<div class="framework-card">
  <div class="client-name">{escape(f['framework_name'])}</div>
  <div class="client-meta">{escape(t(lang,'col.version'))}: <code>{escape(f['framework_version'])}</code>
   · {escape(format_percent(ratio, lang=lang))}</div>
  {progress_bar(ratio)}
  <div class="framework-stats">
    <div class="mini-stat"><strong>{fully}</strong><span>{escape(t(lang,'client.fully'))}</span></div>
    <div class="mini-stat"><strong>{partial}</strong><span>{escape(t(lang,'client.partial'))}</span></div>
    <div class="mini-stat"><strong>{unmapped}</strong><span>{escape(t(lang,'col.unmapped'))}</span></div>
  </div>
</div>"""
        )

    status_badges = " ".join(
        f"{status_badge(lang, k)} <span class='client-meta'>{v}</span>"
        for k, v in dash.status_counts.items()
        if v
    ) or escape(t(lang, "client.none"))

    workload = "".join(
        f"<li>{escape(o)}: {n} {escape(t(lang,'client.open_controls'))}</li>"
        for o, n in dash.workload_by_owner.items()
    ) or f"<li>{escape(t(lang,'client.none'))}</li>"
    deadlines = "".join(
        f"<li>{escape(format_display_date(d['due_date'], lang=lang))} "
        f"<code>{escape(d['control_ref'] or '')}</code>: {escape(d['name'])} "
        f"({escape(t(lang,'col.owner'))}: {escape(d['owner'] or '—')})</li>"
        for d in dash.deadlines_next_30_days
    ) or f"<li>{escape(t(lang,'client.none'))}</li>"
    impact = "".join(
        f"<li><code>{escape(i['canonical_control_ref'] or '')}</code> "
        f"{escape(i['summary'])}</li>"
        for i in dash.top_impact
    ) or f"<li>{escape(t(lang,'client.none'))}</li>"

    ready = "".join(
        "<tr>"
        f"<td>{escape(r['framework_name'])}</td>"
        f"<td><code>{escape(r['framework_version'])}</code></td>"
        f"<td><div class='readiness-cell'><strong>{escape(format_percent(r['implementation_readiness'], lang=lang))}</strong>"
        f"{progress_bar(r['implementation_readiness'])}</div></td>"
        f"<td>{r['fully_covered']}</td><td>{r['partially_covered']}</td>"
        f"<td>{r['not_covered']}</td><td>{r['unmapped']}</td><td>{r['not_applicable']}</td>"
        "</tr>"
        for r in dash.readiness
    )
    ready_table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.framework'))}</th><th>{escape(t(lang,'col.version'))}</th>
<th>{escape(t(lang,'col.readiness'))}</th>
<th>{escape(t(lang,'client.fully'))}</th><th>{escape(t(lang,'client.partial'))}</th>
<th>{escape(t(lang,'client.not_covered'))}</th><th>{escape(t(lang,'col.unmapped'))}</th>
<th>{escape(t(lang,'status.not_applicable'))}</th>
</tr></thead><tbody>{ready}</tbody></table>"""

    metrics = f"""
<div class="grid grid-4" style="margin-bottom:14px">
{metric_card(label=t(lang,'client.unified'), value=format_number(dash.unified_controls, lang=lang), icon_name='shield')}
{metric_card(label=t(lang,'client.missing_evidence'), value=format_number(dash.missing_evidence, lang=lang), icon_name='paperclip')}
{metric_card(label=t(lang,'client.open_tasks'), value=format_number(dash.open_tasks, lang=lang), icon_name='checklist')}
{metric_card(label=t(lang,'client.overdue_tasks'), value=format_number(dash.overdue_tasks, lang=lang), icon_name='clock', tone='danger' if dash.overdue_tasks else '')}
</div>"""

    scope_html = (
        f"<div class='client-meta'>{escape(getattr(dash, 'scope', '') or '')}</div>"
        if getattr(dash, "scope", "")
        else ""
    )
    new_fw = [
        v
        for v in (getattr(dash, "available_framework_versions", None) or [])
        if not v.get("assigned_to_program")
    ]
    from engine.ui_labels import framework_status_label

    new_fw_bits = []
    for v in new_fw:
        fw_name = v.get("framework_name", "")
        cur = next(
            (
                f.get("framework_version")
                for f in dash.frameworks
                if f.get("framework_name") == fw_name or f.get("framework_id") == v.get("framework_id")
            ),
            "—",
        )
        new_v = str(v.get("framework_version") or v.get("version") or "")
        new_fw_bits.append(
            f"<div><strong>{escape(fw_name)}</strong> "
            f"<code>{escape(str(cur))}</code> → <code>{escape(new_v)}</code> "
            f"· {escape(framework_status_label(lang, v.get('status')))}</div>"
        )
    new_fw_html = (
        "<div class='mapping-delta' style='margin-top:8px'><strong>Nuova versione disponibile</strong><br>"
        + "".join(new_fw_bits)
        + f"<div style='margin-top:8px'><a class='btn sm' href='/frameworks/detail?framework_id="
        + escape(str(new_fw[0].get('framework_id') or ''))
        + f"&{nav_qs}'>Confronta versioni</a></div>"
        + "<div class='client-meta'>Nessun aggiornamento automatico della baseline cliente.</div>"
        + "</div>"
        if new_fw
        else ""
    )
    baseline_bits = " · ".join(
        f"{escape(f['framework_name'])} <code>{escape(f['framework_version'])}</code> · Baseline bloccata"
        for f in dash.frameworks
    )
    body = f"""
{page_header(eyebrow=t(lang,'client.eyebrow'), title=dash.tenant_name, subtitle=escape(dash.program_name))}
<div class="client-summary">
  <div class="client-logo" style="width:42px;height:42px">{escape(client_initials(dash.tenant_name))}</div>
  <div>
    <div class="client-summary-title" style="font-size:15px;font-weight:750">{escape(dash.tenant_name)}</div>
    <div class="client-meta"><strong>Programma:</strong> {escape(dash.program_name)}</div>
    {scope_html or "<div class='client-meta'><strong>Scope:</strong> —</div>"}
    <div class="client-meta"><strong>Baseline:</strong> {baseline_bits}</div>
    <div class="client-meta">{dash.raw_requirements} {escape(t(lang,'client.raw'))}
 · {dash.unified_controls} {escape(t(lang,'client.unified'))} · {dash.unmapped_count} {escape(t(lang,'client.unmapped'))}</div>
    {new_fw_html}
  </div>
</div>
{metrics}
<h2>{escape(t(lang,'client.frameworks'))}</h2>
<div class="grid grid-3" style="margin-bottom:14px">{''.join(fw_cards)}</div>
<h2>{escape(t(lang,'client.impl_status'))}</h2>
<p class="meta">{status_badges}</p>
<h2>{escape(t(lang,'client.readiness'))}</h2>
{table_wrap(ready_table)}
<div class="grid grid-2">
  <div class="panel"><div class="panel-head"><div class="panel-title">{escape(t(lang,'client.workload'))}</div></div>
  <div class="panel-body"><ul class="compact">{workload}</ul></div></div>
  <div class="panel"><div class="panel-head"><div class="panel-title">{escape(t(lang,'client.deadlines_30'))}</div></div>
  <div class="panel-body"><ul class="compact">{deadlines}</ul></div></div>
</div>
<div class="panel" style="margin-top:14px"><div class="panel-head"><div class="panel-title">{escape(t(lang,'client.top_impact'))}</div></div>
<div class="panel-body"><ul class="compact">{impact}</ul></div></div>
"""
    return _shell(
        f"{dash.tenant_name} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/client",
        breadcrumb=dash.tenant_name,
    )


def gaps_page(rows, nav_qs: str, filter_values: dict, lang: str | None = None) -> str:
    lang = normalize_lang(str(filter_values.get("lang") or lang or _lang(nav_qs)))
    nav_qs = with_lang(nav_qs, lang)
    opts_status = ["", "IMPLEMENTED", "IN_PROGRESS", "NOT_IMPLEMENTED", "UNMAPPED", "NOT_APPLICABLE"]
    status_opts = "".join(
        f"<option value='{s}' {'selected' if filter_values.get('status')==s else ''}>"
        f"{escape(status_label(lang, s) if s else '—')}</option>"
        for s in opts_status
    )
    mapped_val = filter_values.get("mapped", "")

    from engine.product_pages import gap_taxonomy_label

    critical = sum(
        1
        for r in rows
        if (r.priority or "").upper() == "HIGH"
        and (r.status or "").upper() == "NOT_IMPLEMENTED"
    )
    high = sum(1 for r in rows if (r.priority or "").upper() == "HIGH")
    partial = sum(1 for r in rows if (r.mapping or "").upper() == "PARTIAL")
    unmapped_n = sum(1 for r in rows if not r.mapped or (r.mapping or "").upper() == "UNMAPPED")
    overdue_n = sum(1 for r in rows if r.deadline and is_overdue(r.deadline))
    findings_total = len(rows)
    req_with_issues = len({r.requirement_id for r in rows})

    body_rows = []
    for r in rows:
        if r.canonical_control_ref:
            ctrl_qs = _with_control(nav_qs, r.canonical_control_ref)
            ctrl_cell = (
                f"<a href='/control?{ctrl_qs}'><span class='control-code'>{escape(r.canonical_control_ref)}</span></a>"
                f"<div class='control-title'>{escape(r.control_name or '')}</div>"
            )
        else:
            ctrl_cell = "—"
        tax = gap_taxonomy_label(getattr(r, "taxonomy", "") or "")
        body_rows.append(
            "<tr>"
            f"<td>{priority_badge(lang, r.priority) if r.priority else '—'}</td>"
            f"<td><span class='badge'>{escape(tax)}</span></td>"
            f"<td><strong>{escape(r.requirement_code)}</strong><div class='client-meta'>{escape(r.requirement_title)}</div></td>"
            f"<td>{escape(r.framework_name)}<div class='client-meta'><code>{escape(r.framework_version)}</code></div></td>"
            f"<td>{ctrl_cell}</td>"
            f"<td>{escape(r.gap or '—')}</td>"
            f"<td>{escape(r.owner or '—')}</td>"
            f"<td class='{'overdue' if r.deadline and is_overdue(r.deadline) else ''}'>"
            f"{escape(format_display_date(r.deadline, lang=lang))}</td>"
            f"<td>{status_badge(lang, r.status)}</td>"
            f"<td>{mapping_badge(lang, r.mapping)}</td>"
            "</tr>"
        )

    table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.severity'))}</th>
<th>{escape(t(lang,'gaps.taxonomy'))}</th>
<th>{escape(t(lang,'col.requirement'))}</th>
<th>{escape(t(lang,'col.framework'))}</th>
<th>{escape(t(lang,'col.control'))}</th>
<th>{escape(t(lang,'col.gap'))} / {escape(t(lang,'col.delta'))}</th>
<th>{escape(t(lang,'col.owner'))}</th>
<th>{escape(t(lang,'col.deadline'))}</th>
<th>{escape(t(lang,'col.status'))}</th>
<th>{escape(t(lang,'col.mapping'))}</th>
</tr></thead><tbody>{''.join(body_rows) or f'<tr><td colspan="10">{escape(t(lang,"gaps.empty"))}</td></tr>'}</tbody></table>"""

    summary = f"""
<div class="gap-summary">
  <div class="gap-stat"><div class="gap-stat-label">{escape(t(lang,'gaps.req_with_issues'))}</div><div class="gap-stat-value">{req_with_issues}</div></div>
  <div class="gap-stat"><div class="gap-stat-label">{escape(t(lang,'gaps.findings_total'))}</div><div class="gap-stat-value">{findings_total}</div></div>
  <div class="gap-stat"><div class="gap-stat-label">{escape(t(lang,'gaps.stat.critical'))}</div><div class="gap-stat-value text-danger">{critical}</div></div>
  <div class="gap-stat"><div class="gap-stat-label">{escape(t(lang,'gaps.stat.high'))}</div><div class="gap-stat-value">{high}</div></div>
  <div class="gap-stat"><div class="gap-stat-label">{escape(t(lang,'gaps.stat.partial'))}</div><div class="gap-stat-value text-warning">{partial}</div></div>
  <div class="gap-stat"><div class="gap-stat-label">{escape(t(lang,'gaps.stat.unmapped'))}</div><div class="gap-stat-value">{unmapped_n}</div></div>
  <div class="gap-stat"><div class="gap-stat-label">{escape(t(lang,'gaps.stat.overdue'))}</div><div class="gap-stat-value text-danger">{overdue_n}</div></div>
</div>"""

    body = f"""
{page_header(eyebrow=t(lang,'gaps.eyebrow'), title=t(lang,'gaps.title'), subtitle=f"{req_with_issues} {t(lang,'gaps.req_with_issues').lower()} · {findings_total} {t(lang,'gaps.findings_total').lower()}")}
{summary}
<form class="filters" method="get" action="/gaps">
  <input type="hidden" name="lang" value="{escape(lang)}">
  <input type="hidden" name="superuser" value="{escape(filter_values.get('superuser',''))}">
  <input type="hidden" name="actor_tenants" value="{escape(filter_values.get('actor_tenants',''))}">
  <input type="hidden" name="program_id" value="{escape(filter_values.get('program_id',''))}">
  <label>{escape(t(lang,'col.framework'))}<input name="framework" value="{escape(filter_values.get('framework',''))}"></label>
  <label>{escape(t(lang,'col.status'))}<select name="status">{status_opts}</select></label>
  <label>{escape(t(lang,'col.owner'))}<input name="owner" value="{escape(filter_values.get('owner',''))}"></label>
  <label>{escape(t(lang,'col.priority'))}<input name="priority" value="{escape(filter_values.get('priority',''))}"></label>
  <label>{escape(t(lang,'gaps.deadline_from'))}<input type="date" name="deadline_after" value="{escape(filter_values.get('deadline_after',''))}"></label>
  <label>{escape(t(lang,'gaps.deadline_to'))}<input type="date" name="deadline_before" value="{escape(filter_values.get('deadline_before',''))}"></label>
  <label>{escape(t(lang,'gaps.mapped'))}
    <select name="mapped">
      <option value="" {'selected' if mapped_val=='' else ''}>—</option>
      <option value="1" {'selected' if mapped_val=='1' else ''}>{escape(t(lang,'gaps.mapped'))}</option>
      <option value="0" {'selected' if mapped_val=='0' else ''}>{escape(t(lang,'gaps.unmapped'))}</option>
    </select>
  </label>
  <label>{escape(t(lang,'gaps.missing_ev'))}
    <select name="missing_evidence">
      <option value="" {'selected' if not filter_values.get('missing_evidence') else ''}>—</option>
      <option value="1" {'selected' if filter_values.get('missing_evidence')=='1' else ''}>{escape(t(lang,'gaps.yes'))}</option>
    </select>
  </label>
  <label>{escape(t(lang,'gaps.search'))}<input name="search" value="{escape(filter_values.get('search',''))}"></label>
  <button type="submit" class="btn primary">{escape(t(lang,'gaps.filter'))}</button>
</form>
<div class="panel">{table_wrap(table)}</div>
"""
    return _shell(
        f"{t(lang,'gaps.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/gaps",
        breadcrumb=t(lang, "gaps.title"),
    )


def control_page(detail, nav_qs: str, lang: str | None = None) -> str:
    lang = _lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)

    cov_cards = []
    for c in detail.framework_coverage:
        delta = (
            f"<div class='mapping-delta'><strong>Delta</strong><br>{escape(c.uncovered_delta)}</div>"
            if c.uncovered_delta
            else ""
        )
        cov_cards.append(
            f"""<div class="mapping-card">
  <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
    <div>
      <div class="control-title">{escape(c.framework_name)}</div>
      <div class="client-meta"><code>{escape(c.framework_version)}</code> · {escape(c.requirement_code)}</div>
      <div class="client-meta">{escape(c.requirement_title)}</div>
    </div>
    {mapping_badge(lang, c.relation)}
  </div>
  {delta}
</div>"""
        )

    body = f"""
{page_header(
    eyebrow=t(lang,'control.eyebrow'),
    title=detail.name or detail.control_ref,
    subtitle=t(lang,'control.subtitle'),
    actions_html=(
        f"<a class='btn ghost' href='/checklist?{nav_qs}'>{escape(t(lang,'control.back_list'))}</a>"
        f"<a class='btn primary' href='/control/edit?control_ref={escape(detail.control_ref)}&{nav_qs}'>Modifica</a>"
        f"<a class='btn' href='/evidence?{nav_qs}'>{escape(t(lang,'control.evidence_view'))}</a>"
        f"<a class='btn' href='/tasks?{nav_qs}'>{escape(t(lang,'control.task_view'))}</a>"
    ),
)}
<div class="tabs">
  <a class="active" href="#impl">Implementazione</a>
  <a href="#coverage">Copertura framework</a>
  <a href="#evidence">Evidenze</a>
  <a href="#tasks">Attività</a>
</div>
<div class="panel" style="margin-bottom:14px" id="impl">
  <div class="panel-head"><div class="panel-title">{escape(t(lang,'control.implementation'))}</div></div>
  <div class="panel-body">
    <div class="detail-grid">
      <div class="field"><label>{escape(t(lang,'col.control'))}</label><div class="field-value"><code>{escape(detail.control_ref)}</code></div></div>
      <div class="field"><label>{escape(t(lang,'col.status'))}</label><div class="field-value">{status_badge(lang, detail.status)}</div></div>
      <div class="field"><label>{escape(t(lang,'col.priority'))}</label><div class="field-value">{priority_badge(lang, detail.priority)}</div></div>
      <div class="field"><label>{escape(t(lang,'col.owner'))}</label><div class="field-value">{escape(detail.owner or '—')}</div></div>
      <div class="field"><label>{escape(t(lang,'col.deadline'))}</label><div class="field-value">{escape(format_display_date(detail.due_date, lang=lang))}</div></div>
      <div class="field"><label>{escape(t(lang,'col.evidence'))}</label><div class="field-value">{detail.evidence_count}</div></div>
      <div class="field"><label>{escape(t(lang,'col.tasks'))}</label><div class="field-value">{detail.open_task_count}</div></div>
      <div class="field"><label>{escape(t(lang,'col.notes'))}</label><div class="field-value">{escape(detail.gap_notes or '—')}</div></div>
    </div>
    {f"<p class='meta' style='margin-top:12px'>{escape(detail.description)}</p>" if getattr(detail, 'description', '') else ''}
    {f"<div class='mapping-delta' style='margin-top:10px'><strong>Motivazione N/A</strong><br>{escape(getattr(detail,'not_applicable_rationale','') or '')}"
     f"<div class='client-meta'>Approvato da: {escape(str(getattr(detail,'not_applicable_approved_by', None) or '—'))}"
     f" · {escape(format_display_date(getattr(detail,'not_applicable_approved_at', None), lang=lang))}</div></div>"
     if str(getattr(detail,'status','')).endswith('NOT_APPLICABLE') or str(getattr(detail,'status','')) == 'NOT_APPLICABLE' else ''}
    {f"<div class='mapping-delta' style='margin-top:12px'><strong>{escape(t(lang,'status.not_applicable'))}</strong><br>{escape(detail.not_applicable_rationale)}</div>" if getattr(detail, 'not_applicable_rationale', '') else ''}
    {('<div class="client-meta" style="margin-top:12px"><strong>' + escape(t(lang,'evidence.title')) + '</strong><ul>' + ''.join(f'<li>{escape(x)}</li>' for x in (detail.evidence_titles or [])) + '</ul></div>') if getattr(detail, 'evidence_titles', None) else ''}
    {('<div class="client-meta" style="margin-top:8px"><strong>' + escape(t(lang,'tasks.title')) + '</strong><ul>' + ''.join(f'<li>{escape(x)}</li>' for x in (detail.task_titles or [])) + '</ul></div>') if getattr(detail, 'task_titles', None) else ''}
  </div>
</div>
<div class="panel">
  <div class="panel-head"><div class="panel-title">{escape(t(lang,'control.coverage'))}</div></div>
  <div class="panel-body">
    {''.join(cov_cards) or f"<p class='meta'>{escape(t(lang,'control.no_coverage'))}</p>"}
  </div>
</div>
"""
    return _shell(
        f"{t(lang,'control.title')} — {detail.control_ref}",
        nav_qs,
        body,
        lang=lang,
        active_path="/control",
        breadcrumb=detail.control_ref,
    )


def owners_page(by_owner: dict, nav_qs: str, lang: str | None = None) -> str:
    lang = _lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    sections = []
    for owner, items in by_owner.items():
        row_parts = []
        for i in items:
            if i.control_ref:
                ctrl = (
                    f"<a href='/control?{_with_control(nav_qs, i.control_ref)}'>"
                    f"<span class='control-code'>{escape(i.control_ref)}</span></a>"
                )
            else:
                ctrl = "—"
            row_parts.append(
                "<tr>"
                f"<td>{ctrl}</td>"
                f"<td>{escape(i.name)}</td>"
                f"<td>{status_badge(lang, i.status)}</td>"
                f"<td>{priority_badge(lang, i.priority)}</td>"
                f"<td>{escape(format_display_date(i.due_date, lang=lang))}</td>"
                f"<td>{i.open_task_count}</td>"
                f"<td>{framework_chips(i.frameworks)}</td>"
                "</tr>"
            )
        rows = "".join(row_parts)
        table = (
            f"<table class='data-table'><thead><tr><th>{escape(t(lang,'col.control'))}</th>"
            f"<th>{escape(t(lang,'col.name'))}</th><th>{escape(t(lang,'col.status'))}</th>"
            f"<th>{escape(t(lang,'col.priority'))}</th><th>{escape(t(lang,'col.deadline'))}</th>"
            f"<th>{escape(t(lang,'col.tasks'))}</th><th>{escape(t(lang,'col.framework'))}</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
        )
        sections.append(
            f"<div class='panel' style='margin-bottom:14px'>"
            f"<div class='panel-head'><div class='panel-title'>{escape(owner)}</div>"
            f"<div class='panel-head-spacer'></div><span class='badge neutral'>{len(items)}</span></div>"
            f"{table_wrap(table)}</div>"
        )
    body = (
        page_header(
            eyebrow=t(lang, "owners.eyebrow"),
            title=t(lang, "owners.title"),
            subtitle=t(lang, "owners.meta"),
        )
        + (
            "".join(sections)
            or empty_state(title=t(lang, "owners.empty"), body=t(lang, "owners.meta"))
        )
    )
    return _shell(
        f"{t(lang,'owners.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/owners",
        breadcrumb=t(lang, "owners.title"),
    )


def deadlines_page(items, nav_qs: str, lang: str | None = None) -> str:
    lang = _lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = "".join(
        "<tr>"
        f"<td class='{'overdue' if i.overdue else ''}'>{escape(format_display_date(i.due_date, lang=lang))}</td>"
        f"<td>{escape(i.owner or '—')}</td>"
        f"<td><span class='control-code'>{escape(i.control_ref or '')}</span></td>"
        f"<td>{escape(i.name)}</td>"
        f"<td>{status_badge(lang, i.status)}</td>"
        f"<td>{priority_badge(lang, i.priority)}</td>"
        f"<td>{escape(t(lang,'deadlines.overdue') if i.overdue else t(lang,'deadlines.upcoming'))}</td>"
        "</tr>"
        for i in items
    )
    table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.deadline'))}</th><th>{escape(t(lang,'col.owner'))}</th>
<th>{escape(t(lang,'col.control'))}</th><th>{escape(t(lang,'col.name'))}</th>
<th>{escape(t(lang,'col.status'))}</th><th>{escape(t(lang,'col.priority'))}</th>
<th>{escape(t(lang,'col.flag'))}</th>
</tr></thead><tbody>{rows or f'<tr><td colspan="7">{escape(t(lang,"deadlines.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
{page_header(eyebrow=t(lang,'deadlines.eyebrow'), title=t(lang,'deadlines.title'), subtitle=t(lang,'deadlines.meta'))}
<div class="panel">{table_wrap(table)}</div>
"""
    return _shell(
        f"{t(lang,'deadlines.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/deadlines",
        breadcrumb=t(lang, "deadlines.title"),
    )


def evidence_page(items, nav_qs: str, lang: str | None = None) -> str:
    lang = _lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = "".join(
        "<tr>"
        f"<td><code>{escape(getattr(i, 'evidence_id', None) or '')}</code></td>"
        f"<td>{escape(i.name)}"
        + (
            f"<div class='client-meta'>{escape(getattr(i, 'filename', None) or '')}</div>"
            if getattr(i, "filename", None)
            else ""
        )
        + (
            f"<div class='client-meta'>{escape(t(lang, 'evidence.linked_n', n=2 if getattr(i, 'shared', False) else 1))}</div>"
            if getattr(i, "evidence_id", None)
            else ""
        )
        + (
            f"<div class='client-meta' style='color:var(--wf-warning)'>Finding controllo: evidenza aggiuntiva richiesta</div>"
            if getattr(i, "missing", False) and getattr(i, "evidence_id", None)
            else ""
        )
        + "</td>"
        f"<td><span class='control-code'>{escape(i.control_ref or '')}</span></td>"
        f"<td>{status_badge(lang, i.status)}</td>"
        f"<td>{escape(i.owner or '—')}</td>"
        f"<td>{escape(format_display_date(getattr(i, 'valid_until', None) or i.due_date, lang=lang))}</td>"
        f"<td>{framework_chips(i.frameworks)}</td>"
        + (
            f"<td><a class='btn sm' href='/api/evidence/{escape(getattr(i, 'evidence_id', '') or '')}/download?{nav_qs}'>Scarica</a></td>"
            if getattr(i, "evidence_id", None)
            else "<td>—</td>"
        )
        + "</tr>"
        for i in items
    )
    table = f"""<table class="data-table"><thead><tr>
<th>ID</th><th>{escape(t(lang,'col.name'))}</th>
<th>{escape(t(lang,'col.control'))}</th>
<th>{escape(t(lang,'col.status'))}</th><th>{escape(t(lang,'col.owner'))}</th>
<th>Validità</th>
<th>{escape(t(lang,'col.framework'))}</th><th></th>
</tr></thead><tbody>{rows}</tbody></table>"""
    body = f"""
{page_header(
    eyebrow=t(lang,'evidence.eyebrow'),
    title=t(lang,'evidence.title'),
    subtitle=t(lang,'evidence.meta'),
    actions_html=f"<a class='btn primary' href='/evidence/new?{nav_qs}'>{escape(t(lang,'evidence.upload'))}</a>",
)}
<div class="panel">{table_wrap(table)}</div>
"""
    return _shell(
        f"{t(lang,'evidence.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/evidence",
        breadcrumb=t(lang, "evidence.title"),
    )


def tasks_page(items, nav_qs: str, lang: str | None = None) -> str:
    lang = _lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)

    def _task_extra(i) -> str:
        st = str(getattr(i, "task_status", None) or i.status or "").upper()
        if st in {"DONE", "COMPLETED"}:
            return ""  # completed tasks must not show "Aperta"
        if i.overdue:
            return f"<div class='client-meta' style='color:var(--wf-danger)'>{escape(t(lang,'deadlines.overdue'))}</div>"
        return ""

    rows = "".join(
        "<tr>"
        f"<td><code>{escape(getattr(i, 'task_id', None) or '')}</code></td>"
        f"<td><span class='control-code'>{escape(i.control_ref or '')}</span></td>"
        f"<td>{escape(i.name)}{_task_extra(i)}</td>"
        f"<td>{escape(i.owner or '—')}</td>"
        f"<td class='{'overdue' if i.overdue else ''}'>{escape(format_display_date(i.due_date, lang=lang))}</td>"
        f"<td>{priority_badge(lang, i.priority)}</td>"
        f"<td>{status_badge(lang, getattr(i, 'task_status', None) or i.status)}</td>"
        f"<td><a class='btn sm' href='/tasks/edit?task_id={escape(getattr(i,'task_id','') or '')}&{nav_qs}'>Modifica</a></td>"
        "</tr>"
        for i in items
    )
    table = f"""<table class="data-table"><thead><tr>
<th>ID</th><th>{escape(t(lang,'col.control'))}</th><th>{escape(t(lang,'col.name'))}</th>
<th>{escape(t(lang,'col.owner'))}</th><th>{escape(t(lang,'col.deadline'))}</th>
<th>{escape(t(lang,'col.priority'))}</th><th>{escape(t(lang,'col.status'))}</th>
<th></th>
</tr></thead><tbody>{rows or f'<tr><td colspan="8">{escape(t(lang,"tasks.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
{page_header(
    eyebrow=t(lang,'tasks.eyebrow'),
    title=t(lang,'tasks.title'),
    subtitle=t(lang,'tasks.meta'),
    actions_html=f"<a class='btn primary' href='/tasks/new?{nav_qs}'>+ Nuova attività</a>",
)}
<div class="panel">{table_wrap(table)}</div>
"""
    return _shell(
        f"{t(lang,'tasks.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/tasks",
        breadcrumb=t(lang, "tasks.title"),
    )


__all__ = [
    "portfolio_page",
    "client_page",
    "gaps_page",
    "control_page",
    "owners_page",
    "deadlines_page",
    "evidence_page",
    "tasks_page",
    "lang_from_qs",
]

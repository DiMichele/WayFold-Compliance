"""Dense HTML for Regulatory Intelligence inbox."""

from __future__ import annotations

from html import escape
from urllib.parse import parse_qsl

from engine.dates import format_display_datetime
from engine.i18n import DEFAULT_LANG, normalize_lang, t, with_lang
from engine.ui_components import page_header
from engine.ui_labels import relevance_label, review_label
from engine.ui_shell import render_shell, table_wrap

def _resolve_lang(nav_qs: str, lang: str | None) -> str:
    if lang:
        return normalize_lang(lang)
    return normalize_lang(dict(parse_qsl(nav_qs)).get("lang", DEFAULT_LANG))


def _shell(title: str, nav_qs: str, body: str, *, lang: str, active_path: str) -> str:
    return render_shell(
        title,
        with_lang(nav_qs, lang),
        body,
        lang=lang,
        active_path=active_path,
        breadcrumb=title.split(" — ")[0],
    )


def sources_page(sources, nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = "".join(
        "<tr>"
        f"<td><code>{escape(s.id)}</code></td>"
        f"<td>{escape(s.title)}</td>"
        f"<td>{escape(s.type.value)}</td>"
        f"<td>{escape(s.url)}</td>"
        f"<td>{escape(t(lang,'sources.yes') if s.monitoring_enabled else t(lang,'sources.no'))}</td>"
        f"<td>{escape(s.last_successful_fetch or '—')}</td>"
        f"<td><code>{escape((s.last_content_hash or '')[:12] or '—')}</code></td>"
        f"<td><a href='/api/regulatory/check?{nav_qs}&source_id={escape(s.id)}'>{escape(t(lang,'sources.check'))}</a></td>"
        "</tr>"
        for s in sources
    )
    table = f"""<table><thead><tr>
<th>{escape(t(lang,'col.id'))}</th><th>{escape(t(lang,'col.title'))}</th>
<th>{escape(t(lang,'col.type'))}</th><th>{escape(t(lang,'col.url'))}</th>
<th>{escape(t(lang,'col.monitor'))}</th><th>{escape(t(lang,'col.last_ok'))}</th>
<th>{escape(t(lang,'col.hash'))}</th><th>{escape(t(lang,'col.action'))}</th>
</tr></thead><tbody>{rows or f'<tr><td colspan="8">{escape(t(lang,"sources.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
{page_header(eyebrow=t(lang,'sources.eyebrow'), title=t(lang,'sources.title'), subtitle=t(lang,'sources.meta'))}
<div class="panel">{table_wrap(table)}</div>
"""
    return _shell(
        f"{t(lang,'sources.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/sources",
    )


def changes_page(changes, nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = "".join(
        "<tr>"
        f"<td>{escape(getattr(c, 'source_title', None) or c.source_id)}</td>"
        f"<td>{escape(getattr(c, 'framework_name', None) or '—')}</td>"
        f"<td>{escape(format_display_datetime(c.detected_at, lang=lang))}</td>"
        f"<td><span class='badge info'>{escape(relevance_label(lang, c.relevance))}</span></td>"
        f"<td><span class='badge warning'>{escape(review_label(lang, c.status.value))}</span></td>"
        f"<td>{escape(c.summary)}</td>"
        f"<td><a class='btn sm' href='/change?{nav_qs}&change_id={escape(c.id)}'>Apri</a></td>"
        "</tr>"
        for c in changes
    )
    table = f"""<table class="data-table"><thead><tr>
<th>Fonte</th><th>Framework</th><th>Data</th><th>Tipo modifica</th><th>Stato</th><th>Sintesi</th><th></th>
</tr></thead><tbody>{rows or f'<tr><td colspan="7">{escape(t(lang,"changes.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
{page_header(eyebrow=t(lang,'changes.eyebrow'), title=t(lang,'changes.title'), subtitle=t(lang,'changes.meta'))}
<div class="panel">{table_wrap(table)}</div>
"""
    return _shell(
        f"{t(lang,'changes.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/changes",
    )


def change_detail_page(change, impact, nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    impact_rows = "".join(
        "<tr>"
        f"<td>{escape(r.tenant_name)}</td>"
        f"<td>{escape(r.program_name)}</td>"
        f"<td>{escape(r.framework_name)} <code>{escape(r.framework_version)}</code></td>"
        f"<td>{escape(', '.join(r.requirement_ids) or '—')}</td>"
        f"<td>{escape(', '.join(r.control_refs) or '—')}</td>"
        "</tr>"
        for r in (impact.rows if impact else [])
    )
    table = f"""<table><thead><tr>
<th>{escape(t(lang,'col.client'))}</th><th>{escape(t(lang,'col.program'))}</th>
<th>{escape(t(lang,'col.framework'))}</th><th>{escape(t(lang,'col.requirements'))}</th>
<th>{escape(t(lang,'col.controls'))}</th>
</tr></thead><tbody>{impact_rows or f'<tr><td colspan="5">{escape(t(lang,"client.none"))}</td></tr>'}</tbody></table>"""
    diff_html = ""
    diff_text = getattr(change, "diff_text", None) or getattr(change, "unified_diff", None) or ""
    if diff_text:
        lines = []
        for line in str(diff_text).splitlines():
            cls = "diff-add" if line.startswith("+") else "diff-del" if line.startswith("-") else ""
            lines.append(f"<div class='{cls}'>{escape(line)}</div>")
        diff_html = f"<pre class='diff'>{''.join(lines)}</pre>"
    body = f"""
<div class="page-head">
<h1>Modifica normativa</h1>
<p class="meta">Fonte: {escape(getattr(change, 'source_title', None) or change.source_id)} ·
{escape(review_label(lang, change.status.value))} · {escape(relevance_label(lang, change.relevance))} ·
{escape(format_display_datetime(change.detected_at, lang=lang))}</p>
<p class="meta">{escape(change.summary)}</p>
{diff_html}
</div>
<p class="meta">
  <a href="/api/regulatory/review?{nav_qs}&change_id={escape(change.id)}&status=ACCEPTED">{escape(t(lang,'change.accept'))}</a> ·
  <a href="/api/regulatory/review?{nav_qs}&change_id={escape(change.id)}&status=IGNORED">{escape(t(lang,'change.ignore'))}</a> ·
  <a href="/api/regulatory/impact?{nav_qs}&change_id={escape(change.id)}">{escape(t(lang,'change.impact_json'))}</a>
</p>
<h2>{escape(t(lang,'change.impact'))}</h2>
<p class="meta">{escape(t(lang,'col.requirements'))}: {impact.requirements if impact else 0} · {escape(t(lang,'col.controls'))}: {impact.controls if impact else 0}
 · {escape(t(lang,'col.client'))}: {impact.clients if impact else 0} · {escape(t(lang,'col.program'))}: {impact.programs if impact else 0}</p>
{table_wrap(table)}
<h2>{escape(t(lang,'change.diff'))}</h2>
<pre class="diff">{escape(change.raw_diff or '(empty)')}</pre>
"""
    return _shell(
        f"{t(lang,'col.change')} — {change.id}",
        nav_qs,
        body,
        lang=lang,
        active_path="/changes",
    )


def suggestions_page(suggestions, nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = "".join(
        "<tr>"
        f"<td><code>{escape(s.id)}</code></td>"
        f"<td>{escape(s.change_id)}</td>"
        f"<td>{escape(s.suggested_action)}</td>"
        f"<td><span class='badge'>{escape(s.status.value)}</span></td>"
        f"<td>{escape(', '.join(s.framework_ids))}</td>"
        f"<td>{escape(', '.join(s.framework_versions))}</td>"
        f"<td>{escape(s.rationale)}</td>"
        "</tr>"
        for s in suggestions
    )
    table = f"""<table><thead><tr>
<th>{escape(t(lang,'col.id'))}</th><th>{escape(t(lang,'col.change'))}</th>
<th>{escape(t(lang,'col.action'))}</th><th>{escape(t(lang,'col.status'))}</th>
<th>{escape(t(lang,'col.framework'))}</th><th>{escape(t(lang,'col.version'))}</th>
<th>{escape(t(lang,'col.rationale'))}</th>
</tr></thead><tbody>{rows or f'<tr><td colspan="7">{escape(t(lang,"fw_sugg.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
{page_header(eyebrow=t(lang,'nav.section.knowledge'), title=t(lang,'fw_sugg.title'), subtitle=t(lang,'fw_sugg.meta'))}
<div class="panel">{table_wrap(table)}</div>
"""
    return _shell(
        f"{t(lang,'fw_sugg.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/suggestions",
    )

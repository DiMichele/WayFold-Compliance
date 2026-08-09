from __future__ import annotations

from html import escape
from urllib.parse import parse_qsl

from engine.i18n import DEFAULT_LANG, normalize_lang, t, with_lang
from engine.ui_shell import render_shell, table_wrap

from .domain import AutomatedEvidenceRecord, ConnectorConfig

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


def connectors_page(items: list[ConnectorConfig], nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = []
    for c in items:
        rows.append(
            "<tr>"
            f"<td><code>{escape(c.id)}</code></td>"
            f"<td>{escape(c.name)}</td>"
            f"<td>{escape(c.tenant_id)}</td>"
            f"<td><span class='badge'>{escape(c.kind.value)}</span></td>"
            f"<td>{escape(c.provider)}</td>"
            f"<td>{escape(c.last_ingest_status or '-')}</td>"
            f"<td>{escape(c.last_checked_at or '-')}</td>"
            f"<td><a href='/api/auto-evidence/ingest?{nav_qs}&connector_id={escape(c.id)}'>{escape(t(lang,'auto.conn.ingest'))}</a></td>"
            "</tr>"
        )
    table = f"""<table><thead><tr>
<th>{escape(t(lang,'col.id'))}</th><th>{escape(t(lang,'col.name'))}</th>
<th>{escape(t(lang,'col.tenant'))}</th><th>{escape(t(lang,'col.kind'))}</th>
<th>{escape(t(lang,'col.provider'))}</th><th>{escape(t(lang,'col.last_status'))}</th>
<th>{escape(t(lang,'col.last_checked'))}</th><th>{escape(t(lang,'col.action'))}</th>
</tr></thead><tbody>{''.join(rows) or f'<tr><td colspan=8>{escape(t(lang,"auto.conn.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
<div class="page-head">
<h1>{escape(t(lang,'auto.conn.title'))}</h1>
<p class="warn">{escape(t(lang,'auto.conn.warn'))}</p>
</div>
{table_wrap(table)}
"""
    return _shell(
        t(lang, "auto.conn.title"),
        nav_qs,
        body,
        lang=lang,
        active_path="/connectors",
    )


def evidence_page(items: list[AutomatedEvidenceRecord], nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = []
    for r in items:
        review = ""
        if r.review_status.value == "PENDING_REVIEW":
            review = (
                f"<a href='/api/auto-evidence/review?{nav_qs}&evidence_id={escape(r.id)}&status=APPROVED'>{escape(t(lang,'ai.approve'))}</a> · "
                f"<a href='/api/auto-evidence/review?{nav_qs}&evidence_id={escape(r.id)}&status=REJECTED'>{escape(t(lang,'ai.reject'))}</a>"
            )
        rows.append(
            "<tr>"
            f"<td><code>{escape(r.id)}</code></td>"
            f"<td>{escape(r.canonical_control_ref)}</td>"
            f"<td>{escape(r.check_id)}</td>"
            f"<td><span class='badge'>{escape(r.finding_status.value)}</span></td>"
            f"<td><span class='badge'>{escape(r.review_status.value)}</span></td>"
            f"<td>{escape(r.resource_uid)}</td>"
            f"<td>{escape(r.title)}</td>"
            f"<td>{review}</td>"
            "</tr>"
        )
    table = f"""<table><thead><tr>
<th>{escape(t(lang,'col.id'))}</th><th>{escape(t(lang,'col.control'))}</th>
<th>{escape(t(lang,'col.check'))}</th><th>{escape(t(lang,'col.finding'))}</th>
<th>{escape(t(lang,'col.review'))}</th><th>{escape(t(lang,'col.resource'))}</th>
<th>{escape(t(lang,'col.title'))}</th><th>{escape(t(lang,'col.action'))}</th>
</tr></thead><tbody>{''.join(rows) or f'<tr><td colspan=8>{escape(t(lang,"auto.ev.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
<div class="page-head">
<h1>{escape(t(lang,'auto.ev.title'))}</h1>
<p class="warn">{escape(t(lang,'auto.ev.warn'))}</p>
</div>
{table_wrap(table)}
"""
    return _shell(
        t(lang, "auto.ev.title"),
        nav_qs,
        body,
        lang=lang,
        active_path="/auto-evidence",
    )

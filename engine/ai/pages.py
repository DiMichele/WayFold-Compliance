from __future__ import annotations

from html import escape

from urllib.parse import parse_qsl

from engine.i18n import DEFAULT_LANG, normalize_lang, t, with_lang
from engine.ui_shell import render_shell, table_wrap

from .domain import AISuggestion, TenantAISettings

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


def suggestions_page(items: list[AISuggestion], nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    rows = []
    for s in items:
        rows.append(
            "<tr>"
            f"<td><code>{escape(s.id)}</code></td>"
            f"<td>{escape(s.kind.value)}</td>"
            f"<td>{escape(s.tenant_id)}</td>"
            f"<td><span class='badge'>{escape(s.review_status.value)}</span></td>"
            f"<td>{s.confidence:.2f}</td>"
            f"<td>{escape(s.summary)}</td>"
            f"<td>"
            f"<a href='/api/ai/review?{nav_qs}&suggestion_id={escape(s.id)}&status=APPROVED'>{escape(t(lang,'ai.approve'))}</a> · "
            f"<a href='/api/ai/review?{nav_qs}&suggestion_id={escape(s.id)}&status=REJECTED'>{escape(t(lang,'ai.reject'))}</a>"
            f"</td>"
            "</tr>"
        )
    table = f"""<table><thead><tr>
<th>{escape(t(lang,'col.id'))}</th><th>{escape(t(lang,'col.kind'))}</th>
<th>{escape(t(lang,'col.tenant'))}</th><th>{escape(t(lang,'col.status'))}</th>
<th>{escape(t(lang,'col.conf'))}</th><th>{escape(t(lang,'col.summary'))}</th>
<th>{escape(t(lang,'col.review'))}</th>
</tr></thead><tbody>{''.join(rows) or f'<tr><td colspan=7>{escape(t(lang,"ai.sugg.empty"))}</td></tr>'}</tbody></table>"""
    body = f"""
<div class="page-head">
<h1>{escape(t(lang,'ai.sugg.title'))}</h1>
<p class="warn">{escape(t(lang,'ai.sugg.warn'))}</p>
</div>
{table_wrap(table)}
"""
    return _shell(
        f"{t(lang,'ai.sugg.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/ai/suggestions",
    )


def settings_page(settings: TenantAISettings, nav_qs: str, lang: str | None = None) -> str:
    lang = _resolve_lang(nav_qs, lang)
    nav_qs = with_lang(nav_qs, lang)
    state = t(lang, "ai.settings.enabled") if settings.ai_processing_enabled else t(lang, "ai.settings.disabled")
    body = f"""
<div class="page-head">
<h1>{escape(t(lang,'ai.settings.title'))}</h1>
</div>
<p>Tenant <code>{escape(settings.tenant_id)}</code> — AI: <strong>{escape(state)}</strong></p>
<p>
  <a class="btn" href="/api/ai/settings?{nav_qs}&tenant_id={escape(settings.tenant_id)}&enabled=1">{escape(t(lang,'ai.settings.enable'))}</a>
  <a class="btn" href="/api/ai/settings?{nav_qs}&tenant_id={escape(settings.tenant_id)}&enabled=0">{escape(t(lang,'ai.settings.disable'))}</a>
</p>
<p class="warn">{escape(t(lang,'ai.settings.warn'))}</p>
"""
    return _shell(
        f"{t(lang,'ai.settings.title')} — WayFold Compliance",
        nav_qs,
        body,
        lang=lang,
        active_path="/ai/settings",
    )

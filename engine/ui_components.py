"""Shared WayFold Compliance UI primitives (server-rendered HTML)."""

from __future__ import annotations

from html import escape
from typing import Iterable

from engine.ui_icons import icon
from engine.ui_labels import (
    mapping_label,
    mapping_variant,
    priority_label,
    priority_variant,
    status_label,
    status_variant,
)


def page_header(
    *,
    eyebrow: str,
    title: str,
    subtitle: str = "",
    actions_html: str = "",
) -> str:
    sub = f'<p class="subtitle">{escape(subtitle)}</p>' if subtitle else ""
    actions = f'<div class="page-actions">{actions_html}</div>' if actions_html else ""
    return f"""
<div class="page-head">
  <div>
    <div class="eyebrow">{escape(eyebrow)}</div>
    <h1>{escape(title)}</h1>
    {sub}
  </div>
  {actions}
</div>"""


def metric_card(
    *,
    label: str,
    value: str | int,
    footer: str = "",
    icon_name: str = "trend",
    tone: str = "",
) -> str:
    foot = f'<div class="metric-footer">{footer}</div>' if footer else ""
    tone_cls = f" text-{escape(tone)}" if tone else ""
    return f"""
<div class="panel metric">
  <div class="metric-icon">{icon(icon_name)}</div>
  <div class="metric-label">{escape(label)}</div>
  <div class="metric-value{tone_cls}">{escape(str(value))}</div>
  {foot}
</div>"""


def panel(*, title: str, body: str, subtitle: str = "", toolbar: str = "", css_class: str = "") -> str:
    sub = f'<div class="panel-subtitle">{escape(subtitle)}</div>' if subtitle else ""
    tools = f'<div class="panel-head-spacer"></div><div class="panel-toolbar">{toolbar}</div>' if toolbar else ""
    cls = f"panel {css_class}".strip()
    return f"""
<div class="{escape(cls)}">
  <div class="panel-head">
    <div><div class="panel-title">{escape(title)}</div>{sub}</div>
    {tools}
  </div>
  <div class="panel-body">{body}</div>
</div>"""


def status_badge(lang: str, value) -> str:
    label = status_label(lang, value)
    variant = status_variant(value)
    return (
        f'<span class="badge {escape(variant)}">'
        f'<span class="badge-dot" aria-hidden="true"></span>{escape(label)}</span>'
    )


def mapping_badge(lang: str, value) -> str:
    label = mapping_label(lang, value)
    variant = mapping_variant(value)
    return f'<span class="badge {escape(variant)}">{escape(label)}</span>'


def priority_badge(lang: str, value) -> str:
    if value is None or value == "":
        return "—"
    label = priority_label(lang, value)
    variant = priority_variant(value)
    return f'<span class="badge {escape(variant)}">{escape(label)}</span>'


def coverage_pill(framework_short: str, relation: str, lang: str) -> str:
    rel = str(relation).upper()
    cls = "full" if rel == "FULL" else "partial" if rel == "PARTIAL" else "support"
    return (
        f'<span class="coverage-pill {cls}">'
        f'{escape(framework_short)} · {escape(mapping_label(lang, relation))}</span>'
    )


def progress_bar(ratio: float | None, *, css_class: str = "") -> str:
    if ratio is None:
        pct = 0
    else:
        pct = max(0, min(100, int(round(ratio * 100))))
    tone = "success" if pct >= 70 else "warning" if pct >= 40 else "danger"
    cls = f"progress {tone} {css_class}".strip()
    return (
        f'<div class="{escape(cls)}" role="progressbar" aria-valuenow="{pct}" '
        f'aria-valuemin="0" aria-valuemax="100">'
        f'<span style="width:{pct}%"></span></div>'
    )


def empty_state(*, title: str, body: str, action_html: str = "") -> str:
    action = f'<div class="empty-actions">{action_html}</div>' if action_html else ""
    return f"""
<div class="empty-state">
  <div class="empty-icon">{icon("alert")}</div>
  <div class="empty-title">{escape(title)}</div>
  <p class="empty-body">{escape(body)}</p>
  {action}
</div>"""


def framework_chips(names: Iterable[str]) -> str:
    chips = "".join(
        f'<span class="framework-chip">{escape(n)}</span>' for n in names if n
    )
    return f'<div class="framework-chips">{chips or "—"}</div>'


def client_initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def btn(label: str, *, href: str = "", primary: bool = False, css_class: str = "", icon_name: str = "") -> str:
    classes = ["btn"]
    if primary:
        classes.append("primary")
    if css_class:
        classes.append(css_class)
    ic = icon(icon_name) if icon_name else ""
    inner = f"{ic}{escape(label)}"
    cls = " ".join(classes)
    if href:
        return f'<a class="{cls}" href="{escape(href)}">{inner}</a>'
    return f'<button type="button" class="{cls}">{inner}</button>'


def row_action(href: str, *, label: str = "Apri") -> str:
    return (
        f'<a class="row-action" href="{escape(href)}" aria-label="{escape(label)}" title="{escape(label)}">'
        f'{icon("chevron-right")}</a>'
    )

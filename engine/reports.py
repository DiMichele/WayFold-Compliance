from __future__ import annotations

import csv
import io
from datetime import date

from .checklist import build_unified_checklist
from .consultant_views import deadline_view, task_view
from .dates import format_display_date, today
from .domain import ImplementationStatus, ProgramSnapshot
from .gap_assessment import build_gap_rows
from .impact import rank_control_impact
from .readiness import framework_readiness
from html import escape
from urllib.parse import parse_qsl

from .i18n import DEFAULT_LANG, normalize_lang, t, with_lang
from .ui_components import page_header, progress_bar
from .ui_labels import format_percent, status_label
from .ui_shell import render_shell, table_wrap

DISCLAIMER_IT = (
    "Lo stato indicato rappresenta una valutazione dell'implementazione rispetto "
    "ai requisiti configurati nel programma e non costituisce certificazione "
    "o attestazione legale di conformità."
)


def build_report_context(
    program: ProgramSnapshot, *, as_of: date | None = None
) -> dict:
    as_of = as_of or today()
    checklist = build_unified_checklist(program)
    readiness = framework_readiness(program, checklist)
    impact = rank_control_impact(program, checklist)
    gaps = build_gap_rows(program, checklist)
    deadlines = deadline_view(program, checklist, as_of=as_of)
    tasks = task_view(program, checklist, as_of=as_of)

    critical = [
        g
        for g in gaps
        if g.mapped
        and g.status == ImplementationStatus.NOT_IMPLEMENTED.value
        and (g.priority or "").upper() == "HIGH"
    ]
    high = [
        g
        for g in gaps
        if g.mapped
        and g.status != ImplementationStatus.IMPLEMENTED.value
        and (g.priority or "").upper() == "HIGH"
    ]
    in_progress = [
        c for c in checklist.controls if c.status == ImplementationStatus.IN_PROGRESS
    ]
    overdue = [t for t in tasks if t.overdue] + [
        d for d in deadlines if d.overdue and d.open_task_count == 0
    ]

    baselines = [
        {
            "framework_name": r.framework_name,
            "framework_version": r.framework_version,
        }
        for r in readiness
    ]
    return {
        "client": program.tenant_name,
        "tenant_id": program.tenant_id,
        "program": program.program_name,
        "program_id": program.program_id,
        "assessment_date": as_of.isoformat(),
        "scope": program.scope
        or (
            f"{checklist.raw_requirement_count} requisiti / "
            f"{checklist.unified_control_count} controlli unificati"
        ),
        "framework_baselines": baselines,
        "disclaimer": DISCLAIMER_IT,
        "checklist": checklist,
        "readiness": readiness,
        "impact": impact,
        "critical_gaps": critical,
        "high_priority_gaps": high,
        "in_progress": in_progress,
        "overdue_tasks": overdue,
        "upcoming_deadlines": [d for d in deadlines if not d.overdue],
        "unmapped": checklist.unmapped,
        "gaps": gaps,
    }


def report_html(
    program: ProgramSnapshot, *, as_of: date | None = None, nav_qs: str = ""
) -> str:
    ctx = build_report_context(program, as_of=as_of)
    lang = normalize_lang(dict(parse_qsl(nav_qs)).get("lang", DEFAULT_LANG))
    nav_qs = with_lang(nav_qs, lang)
    none = escape(t(lang, "report.none"))
    ready_rows = "".join(
        "<tr>"
        f"<td>{escape(r.framework_name)}</td><td><code>{escape(r.framework_version)}</code></td>"
        f"<td><div class='readiness-cell'><strong>{escape(format_percent(r.implementation_readiness, lang=lang))}</strong>"
        f"{progress_bar(r.implementation_readiness)}</div></td>"
        f"<td>{r.fully_covered}</td><td>{r.partially_covered}</td>"
        f"<td>{r.not_covered}</td><td>{r.unmapped}</td><td>{r.not_applicable}</td>"
        "</tr>"
        for r in ctx["readiness"]
    )
    crit = "".join(
        f"<li>{escape(g.framework_name)} {escape(g.requirement_code)} — "
        f"{escape(g.canonical_control_ref or '—')} ({escape(status_label(lang, g.status))}): {escape(g.gap)}</li>"
        for g in ctx["critical_gaps"][:25]
    ) or f"<li>{none}</li>"
    high = "".join(
        f"<li>{escape(g.framework_name)} {escape(g.requirement_code)} — "
        f"{escape(g.canonical_control_ref or '—')} ({escape(status_label(lang, g.status))})</li>"
        for g in ctx["high_priority_gaps"][:25]
    ) or f"<li>{none}</li>"
    progress = "".join(
        f"<li>{escape(c.canonical_control_ref or '')}: {escape(c.name)} "
        f"({escape(t(lang,'col.owner'))}: {escape(c.owner or '—')}, "
        f"{escape(t(lang,'col.deadline'))}: {escape(format_display_date(c.due_date, lang=lang))})</li>"
        for c in ctx["in_progress"]
    ) or f"<li>{none}</li>"
    overdue = "".join(
        f"<li>{escape(str(getattr(item, 'control_ref', None) or getattr(item, 'name', item)))} "
        f"{escape(t(lang,'col.deadline'))}: {escape(format_display_date(getattr(item, 'due_date', None), lang=lang))} "
        f"{escape(t(lang,'col.owner'))}: {escape(str(getattr(item, 'owner', None) or '—'))}</li>"
        for item in ctx["overdue_tasks"][:25]
    ) or f"<li>{none}</li>"
    upcoming = "".join(
        f"<li>{escape(format_display_date(d.due_date, lang=lang))} {escape(d.control_ref or '')}: {escape(d.name)} "
        f"({escape(t(lang,'col.owner'))}: {escape(d.owner or '—')})</li>"
        for d in ctx["upcoming_deadlines"][:25]
    ) or f"<li>{none}</li>"
    unmapped = "".join(
        f"<li>{escape(u.framework_name)} {escape(u.code)}: {escape(u.title)}</li>"
        for u in ctx["unmapped"]
    ) or f"<li>{none}</li>"
    ready_table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.framework'))}</th><th>{escape(t(lang,'col.version'))}</th>
<th>{escape(t(lang,'col.readiness'))}</th>
<th>{escape(t(lang,'checklist.fully'))}</th><th>{escape(t(lang,'checklist.partial'))}</th>
<th>{escape(t(lang,'checklist.not'))}</th><th>{escape(t(lang,'col.unmapped'))}</th>
<th>{escape(t(lang,'checklist.na'))}</th>
</tr></thead><tbody>{ready_rows}</tbody></table>"""

    body = f"""
{page_header(
    eyebrow=t(lang,'report.eyebrow'),
    title=t(lang,'report.title'),
    subtitle=f"{ctx['client']} · {ctx['program']} · {t(lang,'report.assessment')}: {format_display_date(ctx['assessment_date'], lang=lang)}",
)}
<div class="report-preview">
  <div class="client-name">WayFold Compliance</div>
  <div class="client-meta">{escape(t(lang,'report.title'))}</div>
  <hr class="report-rule" style="border:0;border-top:1px solid var(--wf-border);margin:20px 0">
  <p><strong>Cliente:</strong> {escape(ctx['client'])}<br>
  <strong>Programma:</strong> {escape(ctx['program'])}<br>
  <strong>{escape(t(lang,'report.scope'))}:</strong> {escape(ctx['scope'])}<br>
  <strong>{escape(t(lang,'report.assessment'))}:</strong> {escape(format_display_date(ctx['assessment_date'], lang=lang))}</p>
  <p><strong>Framework + versione:</strong> {escape(', '.join(f"{b['framework_name']}@{b['framework_version']}" for b in ctx['framework_baselines']))}</p>
  <h2>{escape(t(lang,'report.exec'))}</h2>
  <ul class="compact">
  <li>{escape(t(lang,'report.unified'))}: {ctx['checklist'].unified_control_count}</li>
  <li>{escape(t(lang,'report.unmapped_req'))}: {len(ctx['unmapped'])}</li>
  <li>{escape(t(lang,'report.critical'))}: {len(ctx['critical_gaps'])}</li>
  <li>{escape(t(lang,'report.in_progress'))}: {len(ctx['in_progress'])}</li>
  <li>{escape(t(lang,'report.overdue_signals'))}: {len(ctx['overdue_tasks'])}</li>
  </ul>
  <p class="client-meta" style="margin-top:18px;border-left:3px solid var(--wf-border);padding-left:12px">{escape(ctx['disclaimer'])}</p>
  <h2>{escape(t(lang,'report.readiness'))}</h2>
  {table_wrap(ready_table)}
  <h2>{escape(t(lang,'report.critical_gaps'))}</h2><ul class="compact">{crit}</ul>
  <h2>{escape(t(lang,'report.high_gaps'))}</h2><ul class="compact">{high}</ul>
  <h2>{escape(t(lang,'report.controls_progress'))}</h2><ul class="compact">{progress}</ul>
  <h2>{escape(t(lang,'report.overdue'))}</h2><ul class="compact">{overdue}</ul>
  <h2>{escape(t(lang,'report.upcoming'))}</h2><ul class="compact">{upcoming}</ul>
  <h2>{escape(t(lang,'report.unmapped'))}</h2><ul class="compact">{unmapped}</ul>
</div>
"""
    return render_shell(
        f"{t(lang,'nav.report')} — {ctx['client']} / {ctx['program']}",
        nav_qs,
        body,
        lang=lang,
        active_path="/report",
        breadcrumb=t(lang, "report.title"),
    )


def report_csv(program: ProgramSnapshot, *, as_of: date | None = None) -> str:
    ctx = build_report_context(program, as_of=as_of)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "client",
            "program",
            "assessment_date",
            "framework",
            "framework_version",
            "requirement",
            "title",
            "control",
            "mapping",
            "status",
            "owner",
            "deadline",
            "priority",
            "evidence_count",
            "gap",
        ]
    )
    for g in ctx["gaps"]:
        w.writerow(
            [
                ctx["client"],
                ctx["program"],
                ctx["assessment_date"],
                g.framework_name,
                g.framework_version,
                g.requirement_code,
                g.requirement_title,
                g.canonical_control_ref or "",
                g.mapping,
                g.status,
                g.owner or "",
                g.deadline or "",
                g.priority or "",
                g.evidence_count,
                g.gap,
            ]
        )
    return buf.getvalue()

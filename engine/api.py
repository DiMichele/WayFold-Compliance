"""WayFold Compliance — consultant-facing HTTP surface.

Run:
  python -m engine.api
Default: http://127.0.0.1:8092

Auth (production):
  Cookie session via /login (WAYFOLD_AUTH_USER / WAYFOLD_AUTH_PASSWORD).
  Public: /login, /healthz, /api/health.

Auth (local/tests):
  ?superuser=1 OR ?actor_tenants=... when WAYFOLD_ALLOW_QS_AUTH / demo seed enabled.
  WAYFOLD_OPEN_ACCESS=1 still allows anonymous consultant browse (dev only).
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.authz import AuthContext, assert_tenant_access, context_from_session_fields
from engine.checklist import build_unified_checklist
from engine.consultant_views import (
    control_detail,
    deadline_view,
    evidence_view,
    owner_view,
    task_view,
)
from engine.gap_assessment import GapFilter, build_gap_rows, filter_gap_rows
from engine.impact import rank_control_impact
from engine.portfolio import (
    DEFAULT_REGISTRY,
    build_client_dashboard,
    build_portfolio,
    load_portfolio_programs,
)
from engine.program_loader import load_program_snapshot
from engine.readiness import framework_readiness
from engine.reports import report_csv, report_html
from engine.serialize import to_jsonable
from engine.auth_session import (
    auth_configured,
    clear_session_cookie_header,
    forbidden_page_html,
    issue_session,
    login_page_html,
    open_access_enabled,
    qs_auth_allowed,
    refresh_session,
    session_cookie_header,
    session_from_cookie_header,
    wants_html,
)
from engine.rbac import (
    PERM_AUDIT_READ,
    PERM_EVIDENCE_DOWNLOAD,
    PERM_FRAMEWORK_PUBLISH,
    PERM_KB_READ,
    PERM_KB_WRITE,
    PERM_REPORT_GENERATE,
    Role,
    has_permission,
    parse_role,
    role_is_superuser,
)
from engine import audit as audit_mod
from engine import authoring_routes
from engine import evidence_storage
from engine import framework_registry
from engine import framework_versions as fw_versions
from engine import kb_mappings
from engine import product_pages
from engine import program_authoring
from engine import report_snapshots
from engine import control_catalog
from engine.users import (
    authenticate,
    effective_tenant_ids,
    list_users,
    load_assignments,
)
from engine.mfa import mfa_required_for_role, verify_totp
from engine.i18n import lang_from_qs, t, with_lang
from engine.ui_shell import render_shell, table_wrap
from engine import ux_pages
from engine.regulatory.domain import ChangeStatus
from engine.regulatory.pipeline import check_source, impact_for_change, review_change
from engine.regulatory.store import RegulatoryStore
from engine.regulatory import pages as reg_pages
from engine.ai.domain import SuggestionReviewStatus
from engine.ai.service import AIAssistanceService, AIProcessingDisabled
from engine.ai.store import AIStore
from engine.ai import pages as ai_pages
from engine.automated_evidence.domain import EvidenceReviewStatus
from engine.automated_evidence.service import AutomatedEvidenceService
from engine.automated_evidence.store import AutomatedEvidenceStore
from engine.automated_evidence import pages as auto_ev_pages
from engine.runtime_paths import portfolio_registry_path, seed_demo_enabled

DEFAULT_PROGRAM = ROOT / "engine" / "fixtures" / "michele_phase2_program.json"
_REG_STORE: RegulatoryStore | None = None
_AI_SERVICE: AIAssistanceService | None = None
_AUTO_EV_SERVICE: AutomatedEvidenceService | None = None


def _active_registry() -> Path:
    return portfolio_registry_path(DEFAULT_REGISTRY)


def _reg_store() -> RegulatoryStore:
    global _REG_STORE
    if _REG_STORE is None:
        _REG_STORE = RegulatoryStore()
        if seed_demo_enabled() and not _REG_STORE.list_sources():
            from engine.regulatory.demo import seed_demo_source

            seed_demo_source(_REG_STORE)
    return _REG_STORE


def _ai_service() -> AIAssistanceService:
    global _AI_SERVICE
    if _AI_SERVICE is None:
        _AI_SERVICE = AIAssistanceService(
            store=AIStore(), regulatory_store=_reg_store()
        )
    return _AI_SERVICE


def _auto_ev_service() -> AutomatedEvidenceService:
    global _AUTO_EV_SERVICE
    if _AUTO_EV_SERVICE is None:
        store = AutomatedEvidenceStore()
        if seed_demo_enabled() and not store.list_connectors():
            from engine.automated_evidence.demo import seed_demo_connector

            seed_demo_connector(store)
        _AUTO_EV_SERVICE = AutomatedEvidenceService(store=store)
    return _AUTO_EV_SERVICE


def _open_access_enabled() -> bool:
    return open_access_enabled()


def _auth_from_qs(qs: dict) -> tuple[set[str], bool]:
    actor_tenants = {
        t.strip() for t in qs.get("actor_tenants", [""])[0].split(",") if t.strip()
    }
    is_super = qs.get("superuser", ["0"])[0].lower() in {"1", "true", "yes"}
    if open_access_enabled() and not actor_tenants and not is_super:
        return set(), True
    return actor_tenants, is_super


def _auth_context_from_request(handler: "Handler", qs: dict) -> AuthContext | None:
    """Return AuthContext when authenticated; None when anonymous."""
    headers = getattr(handler, "headers", None)
    cookie = headers.get("Cookie") if headers is not None else None
    session = session_from_cookie_header(cookie)
    if session is not None:
        role = parse_role(session.role)
        tenants = set(session.tenant_ids)
        is_super = session.is_superuser or role_is_superuser(role)
        # Sliding session refresh attached for handler to emit
        handler._session_refresh_token = refresh_session(session)  # type: ignore[attr-defined]
        return context_from_session_fields(
            username=session.username,
            role=role,
            tenant_ids=tenants,
            is_superuser=is_super,
            mfa_verified=session.mfa_verified,
        )

    if qs_auth_allowed():
        tenants, is_super = _auth_from_qs(qs)
        if is_super or tenants:
            role = Role.SUPER_ADMIN if is_super else Role.CONSULTANT
            return context_from_session_fields(
                username="qs-auth",
                role=role,
                tenant_ids=tenants,
                is_superuser=is_super,
            )
        if open_access_enabled():
            return context_from_session_fields(
                username="open-access",
                role=Role.SUPER_ADMIN,
                tenant_ids=set(),
                is_superuser=True,
            )

    if open_access_enabled():
        return context_from_session_fields(
            username="open-access",
            role=Role.SUPER_ADMIN,
            tenant_ids=set(),
            is_superuser=True,
        )
    return None


def _auth_from_request(handler: "Handler", qs: dict) -> tuple[set[str], bool, str | None]:
    """Backward-compatible: (actor_tenants, is_superuser, username)."""
    ctx = _auth_context_from_request(handler, qs)
    if ctx is None:
        return set(), False, None
    return ctx.actor_tenant_ids, ctx.is_superuser, ctx.username


def _nav_qs(
    qs: dict,
    *,
    program_id: str | None = None,
    tenant_name: str | None = None,
    program_name: str | None = None,
) -> str:
    actor = qs.get("actor_tenants", [""])[0]
    superuser = qs.get("superuser", ["0"])[0]
    pid = program_id or qs.get("program_id", [""])[0]
    lang = lang_from_qs(qs)
    data = {"lang": lang}
    if superuser in {"1", "true", "yes"}:
        data["superuser"] = "1"
    if actor:
        data["actor_tenants"] = actor
    if pid:
        data["program_id"] = pid
        tname = tenant_name or qs.get("tenant_name", [""])[0]
        pname = program_name or qs.get("program_name", [""])[0]
        if tname:
            data["tenant_name"] = tname
        if pname:
            data["program_name"] = pname
    return urlencode(data)


def _resolve_program(qs: dict):
    """Resolve program snapshot from program_id / path. No demo fallback."""
    program_path = qs.get("program", [None])[0]
    program_id = qs.get("program_id", [None])[0]
    registry = _active_registry()
    if program_path:
        path = Path(program_path)
        if path.is_file():
            return load_program_snapshot(path)
        return None
    if program_id:
        for program, _ in load_portfolio_programs(registry):
            if program.program_id == program_id:
                return program
        return None
    programs = load_portfolio_programs(registry)
    if len(programs) == 1:
        return programs[0][0]
    if seed_demo_enabled() and DEFAULT_PROGRAM.is_file():
        return load_program_snapshot(DEFAULT_PROGRAM)
    return None


_PROGRAM_SCOPED_HTML = frozenset(
    {
        "/checklist",
        "/client",
        "/gaps",
        "/control",
        "/owners",
        "/deadlines",
        "/evidence",
        "/tasks",
        "/report",
        "/mappings",
    }
)

_PATH_TITLE_KEYS = {
    "/portfolio": "portfolio.title",
    "/checklist": "checklist.title",
    "/client": "nav.client",
    "/gaps": "gaps.title",
    "/control": "control.title",
    "/owners": "owners.title",
    "/deadlines": "deadlines.title",
    "/evidence": "evidence.title",
    "/tasks": "tasks.title",
    "/report": "report.title",
    "/sources": "sources.title",
    "/changes": "changes.title",
    "/suggestions": "fw_sugg.title",
    "/connectors": "auto.conn.title",
    "/auto-evidence": "auto.ev.title",
    "/ai/suggestions": "ai.sugg.title",
    "/ai/settings": "ai.settings.title",
}


def _empty_workspace_html(nav_qs: str, *, active_path: str = "/portfolio") -> bytes:
    from urllib.parse import parse_qsl as _pq

    from engine.i18n import normalize_lang
    from engine.ui_components import empty_state, page_header

    lang = normalize_lang(dict(_pq(nav_qs)).get("lang", "it"))
    title_key = _PATH_TITLE_KEYS.get(active_path, "empty.title")
    page_title = t(lang, title_key)
    body = page_header(
        eyebrow="WayFold Compliance",
        title=page_title,
        subtitle=t(lang, "empty.meta"),
    ) + empty_state(
        title=t(lang, "empty.title"),
        body=t(lang, "empty.meta"),
        action_html=(
            f'<a class="btn primary" href="/portfolio?{nav_qs}">'
            f'{t(lang, "nav.portfolio")}</a>'
        ),
    )
    return render_shell(
        f"{page_title} — WayFold Compliance",
        with_lang(nav_qs, lang),
        body,
        lang=lang,
        active_path=active_path,
        breadcrumb=page_title,
    ).encode("utf-8")


def _select_client_html(nav_qs: str, rows, *, active_path: str) -> bytes:
    """Shown when a program-scoped page is opened and multiple clients are available."""
    from html import escape
    from urllib.parse import parse_qsl as _pq

    from engine.i18n import normalize_lang
    from engine.ui_components import page_header

    lang = normalize_lang(dict(_pq(nav_qs)).get("lang", "it"))
    title_key = _PATH_TITLE_KEYS.get(active_path, "empty.title")
    page_title = t(lang, title_key)
    links = []
    for r in rows:
        data = dict(_pq(nav_qs))
        data["program_id"] = r.program_id
        data["lang"] = lang
        qs = urlencode(data)
        links.append(
            "<tr>"
            f"<td><a href='{escape(active_path)}?{qs}'><strong>{escape(r.tenant_name)}</strong></a>"
            f"<div class='client-meta'>{escape(r.program_name)}</div></td>"
            f"<td>{escape(', '.join(r.frameworks))}</td>"
            f"<td><a class='btn sm primary' href='{escape(active_path)}?{qs}'>"
            f"{escape(t(lang, 'action.open'))}</a></td>"
            "</tr>"
        )
    table = (
        f"<table class='data-table'><thead><tr>"
        f"<th>{escape(t(lang, 'col.client'))}</th>"
        f"<th>{escape(t(lang, 'col.framework'))}</th>"
        f"<th></th></tr></thead><tbody>{''.join(links)}</tbody></table>"
    )
    body = (
        page_header(
            eyebrow=page_title,
            title=t(lang, "select_client.title"),
            subtitle=t(lang, "select_client.meta"),
        )
        + f'<div class="panel">{table_wrap(table)}</div>'
    )
    return render_shell(
        f"{page_title} — WayFold Compliance",
        with_lang(nav_qs, lang),
        body,
        lang=lang,
        active_path=active_path,
        breadcrumb=page_title,
    ).encode("utf-8")


def _html_checklist(checklist, readiness, impact, nav_qs: str = "") -> str:
    from html import escape
    from urllib.parse import parse_qsl as _pq

    from engine.dates import format_display_date
    from engine.i18n import normalize_lang
    from engine.ui_components import (
        coverage_pill,
        page_header,
        priority_badge,
        progress_bar,
        status_badge,
    )
    from engine.ui_labels import format_percent

    lang = normalize_lang(dict(_pq(nav_qs)).get("lang", "it"))
    rows = []
    for c in checklist.controls:
        cov = "".join(
            coverage_pill(
                x.framework_name.split()[0] if x.framework_name else "?",
                x.relation.value if hasattr(x.relation, "value") else x.relation,
                lang,
            )
            + (
                f"<div class='client-meta'>{escape(x.requirement_code)}"
                + (f" · delta: {escape(x.uncovered_delta)}" if x.uncovered_delta else "")
                + "</div>"
                if x.requirement_code or x.uncovered_delta
                else ""
            )
            for x in c.framework_coverage
        )
        href = ""
        if c.canonical_control_ref:
            from urllib.parse import parse_qsl, urlencode

            data = dict(parse_qsl(nav_qs, keep_blank_values=False))
            data["control_ref"] = c.canonical_control_ref
            href = f"/control?{urlencode(data)}"
        code_html = (
            f"<a href='{href}'><span class='control-code'>{escape(c.canonical_control_ref or '')}</span></a>"
            if href
            else f"<span class='control-code'>{escape(c.canonical_control_ref or '')}</span>"
        )
        rows.append(
            "<tr>"
            f"<td>{code_html}<div class='control-title'>{escape(c.name)}</div>"
            f"<div class='control-desc'>{escape(c.gap_notes or '')}</div></td>"
            f"<td>{status_badge(lang, c.status.value if hasattr(c.status,'value') else c.status)}</td>"
            f"<td><div class='coverage-list'>{cov or '—'}</div></td>"
            f"<td>{escape(c.owner or '—')}</td>"
            f"<td>{escape(format_display_date(c.due_date, lang=lang))}</td>"
            f"<td>{priority_badge(lang, c.priority)}</td>"
            f"<td>{c.evidence_count}</td>"
            f"<td>{c.open_task_count}</td>"
            "</tr>"
        )
    unmapped = "".join(
        f"<li>{escape(u.framework_name)} <code>{escape(u.code)}</code> — {escape(u.title)}</li>"
        for u in checklist.unmapped
    )
    ready_rows = "".join(
        "<tr>"
        f"<td>{escape(r.framework_name)}</td><td><code>{escape(r.framework_version)}</code></td>"
        f"<td>{r.fully_covered}</td><td>{r.partially_covered}</td>"
        f"<td>{r.not_covered}</td><td>{r.unmapped}</td>"
        f"<td>{r.not_applicable}</td>"
        f"<td><div class='readiness-cell'><strong>{escape(format_percent(r.implementation_readiness, lang=lang))}</strong>"
        f"{progress_bar(r.implementation_readiness)}</div></td>"
        "</tr>"
        for r in readiness
    )
    impact_items = "".join(f"<li>{escape(i.readable_summary)}</li>" for i in impact[:10])
    main_table = f"""<table class="data-table">
<thead><tr>
<th>{escape(t(lang,'col.control'))}</th>
<th>{escape(t(lang,'col.status'))}</th><th>{escape(t(lang,'control.coverage'))}</th>
<th>{escape(t(lang,'col.owner'))}</th><th>{escape(t(lang,'col.deadline'))}</th>
<th>{escape(t(lang,'col.priority'))}</th><th>{escape(t(lang,'col.evidence'))}</th>
<th>{escape(t(lang,'col.tasks'))}</th>
</tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>"""
    ready_table = f"""<table class="data-table"><thead><tr>
<th>{escape(t(lang,'col.framework'))}</th><th>{escape(t(lang,'col.version'))}</th>
<th>{escape(t(lang,'checklist.fully'))}</th><th>{escape(t(lang,'checklist.partial'))}</th>
<th>{escape(t(lang,'checklist.not'))}</th>
<th>{escape(t(lang,'col.unmapped'))}</th><th>{escape(t(lang,'checklist.na'))}</th>
<th>{escape(t(lang,'checklist.impl_ready'))}</th>
</tr></thead><tbody>{ready_rows}</tbody></table>"""
    body = f"""
{page_header(
    eyebrow=t(lang,'checklist.eyebrow'),
    title=t(lang,'checklist.title'),
    subtitle=f"{checklist.program_name} · {t(lang,'checklist.meta')}",
)}
<div class="panel" style="margin-bottom:14px">{table_wrap(main_table)}</div>
<section>
<h2>{escape(t(lang,'checklist.unmapped'))}</h2>
<ul class="compact">{unmapped or f'<li>{escape(t(lang,"client.none"))}</li>'}</ul>
</section>
<section>
<h2>{escape(t(lang,'checklist.readiness'))}</h2>
{table_wrap(ready_table)}
</section>
<section>
<h2>{escape(t(lang,'checklist.impact'))}</h2>
<ul class="compact">{impact_items}</ul>
</section>
"""
    return render_shell(
        f"{t(lang,'checklist.title')} — {checklist.program_name}",
        with_lang(nav_qs, lang),
        body,
        lang=lang,
        active_path="/checklist",
        breadcrumb=t(lang, "checklist.title"),
    )


class Handler(BaseHTTPRequestHandler):
    def _deny(self, code: int, msg: str):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send(
        self,
        code: int,
        body: bytes,
        content_type: str,
        *,
        extra_headers: dict[str, str] | None = None,
    ):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )
        headers = dict(extra_headers or {})
        refresh = getattr(self, "_session_refresh_token", None)
        if refresh and "Set-Cookie" not in headers:
            headers["Set-Cookie"] = session_cookie_header(
                refresh, secure=self._request_is_secure()
            )
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str, *, extra_headers: dict[str, str] | None = None):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _request_is_secure(self) -> bool:
        proto = (self.headers.get("X-Forwarded-Proto") or "").lower()
        return proto == "https"

    def _gate(
        self,
        qs: dict,
        target_tenant_id: str | None = None,
        *,
        permission: str | None = None,
    ):
        from urllib.parse import quote

        ctx = _auth_context_from_request(self, qs)
        if ctx is None or (not ctx.is_superuser and not ctx.actor_tenant_ids):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            headers = getattr(self, "headers", None)
            accept = headers.get("Accept") if headers is not None else None
            if wants_html(accept, path):
                next_path = self.path if self.path.startswith("/") else "/portfolio"
                self._redirect(f"/login?next={quote(next_path, safe='/?&=')}")
                return None
            self._deny(401, "authentication_required")
            return None
        if permission and not has_permission(ctx.role, permission):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            headers = getattr(self, "headers", None)
            accept = headers.get("Accept") if headers is not None else None
            if wants_html(accept, path):
                html = forbidden_page_html(lang=lang_from_qs(qs))
                self._send(403, html.encode("utf-8"), "text/html; charset=utf-8")
                return None
            self._deny(403, "permission_denied")
            return None
        if target_tenant_id is not None:
            decision = assert_tenant_access(
                actor_tenant_ids=ctx.actor_tenant_ids,
                is_superuser=ctx.is_superuser,
                target_tenant_id=target_tenant_id,
            )
            if not decision.allowed:
                audit_mod.record_event(
                    actor_user_id=ctx.username or "unknown",
                    action=audit_mod.ACCESS_DENIED,
                    entity_type="tenant",
                    entity_id=target_tenant_id,
                    tenant_id=target_tenant_id,
                    detail=decision.reason,
                )
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                headers = getattr(self, "headers", None)
                accept = headers.get("Accept") if headers is not None else None
                if wants_html(accept, path):
                    html = forbidden_page_html(lang=lang_from_qs(qs))
                    self._send(403, html.encode("utf-8"), "text/html; charset=utf-8")
                    return None
                self._deny(403, decision.reason)
                return None
        self._auth_ctx = ctx  # type: ignore[attr-defined]
        return ctx.actor_tenant_ids, ctx.is_superuser

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        path = parsed.path.rstrip("/") or "/"

        # Deep-link program context: /clients/:clientId/programs/:programId/...
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 4 and parts[0] == "clients" and parts[2] == "programs":
            client_id, program_id = parts[1], parts[3]
            rest = parts[4] if len(parts) > 4 else "client"
            route_map = {
                "controls": "/checklist",
                "checklist": "/checklist",
                "gaps": "/gaps",
                "evidence": "/evidence",
                "tasks": "/tasks",
                "report": "/report",
                "mappings": "/mappings",
                "client": "/client",
            }
            target = route_map.get(rest, "/client")
            flat = {k: v[0] for k, v in qs.items() if v}
            flat["program_id"] = program_id
            flat.setdefault("client_id", client_id)
            flat.setdefault("lang", lang_from_qs(qs))
            return self._redirect(f"{target}?{urlencode(flat)}")

        if path in {"/api/health", "/healthz"}:
            return self._send(
                200,
                b'{"status":"ok","service":"wayfold-compliance"}',
                "application/json",
            )

        if path == "/login":
            lang = lang_from_qs(qs)
            next_path = qs.get("next", ["/portfolio"])[0] or "/portfolio"
            if not next_path.startswith("/"):
                next_path = "/portfolio"
            # Already authenticated → portfolio
            _t, is_super, _u = _auth_from_request(self, qs)
            if is_super or _t:
                return self._redirect(next_path)
            html = login_page_html(lang=lang, next_path=next_path)
            return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

        if path == "/logout":
            return self._redirect(
                "/login",
                extra_headers={
                    "Set-Cookie": clear_session_cookie_header(secure=self._request_is_secure())
                },
            )

        # Knowledge Base / client-program authoring surfaces
        if path.startswith(
            (
                "/frameworks/new",
                "/frameworks/versions",
                "/frameworks/requirements",
                "/frameworks/publish",
                "/controls",
                "/mappings/new",
                "/clients/new",
                "/programs/new",
                "/control/edit",
                "/api/frameworks/requirements/template.csv",
                "/api/controls",
            )
        ):
            auth = self._gate(qs)
            if auth is None:
                return
            if authoring_routes.handle_authoring_get(self, path, qs, auth):
                return

        # Portfolio (multi-tenant filtered)
        if path in {"/", "/portfolio"}:
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            rows = build_portfolio(
                actor_tenant_ids=actor_tenants,
                is_superuser=is_super,
                registry_path=_active_registry(),
            )
            nav = _nav_qs(qs)
            return self._send(
                200,
                ux_pages.portfolio_page(rows, nav).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/api/portfolio":
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            rows = build_portfolio(
                actor_tenant_ids=actor_tenants,
                is_superuser=is_super,
                registry_path=_active_registry(),
            )
            body = json.dumps(to_jsonable(rows), ensure_ascii=False).encode("utf-8")
            return self._send(200, body, "application/json")

        if path == "/users":
            flat = {k: v[0] for k, v in qs.items() if v}
            flat["tab"] = "users"
            return self._redirect(f"/settings?{urlencode(flat)}")

        if path in {"/evidence/new", "/tasks/new"}:
            auth = self._gate(qs)
            if auth is None:
                return
            nav = _nav_qs(qs)
            title = "Nuova evidenza" if path.endswith("evidence/new") else "Nuova attività"
            target = "/evidence" if "evidence" in path else "/tasks"
            body = (
                f"<div class='page-head'><h1>{title}</h1>"
                f"<p class='subtitle'>Completa i campi e salva. Il collegamento al programma corrente viene preservato.</p></div>"
                f"<form method='post' action='{path}?{nav}' class='panel' style='padding:18px'>"
                f"<div class='form-grid'>"
                f"<div class='form-field full'><label>Titolo / Nome</label><input name='title' required></div>"
                f"<div class='form-field'><label>Owner</label><input name='owner'></div>"
                f"<div class='form-field'><label>Scadenza / Validità</label><input type='date' name='due_date'></div>"
                f"<div class='form-field full'><label>Note</label><textarea name='notes'></textarea></div>"
                f"</div>"
                f"<div class='page-actions' style='margin-top:14px'>"
                f"<button class='btn primary' type='submit'>Salva</button>"
                f"<a class='btn ghost' href='{target}?{nav}'>Annulla</a></div></form>"
            )
            return self._send(
                200,
                render_shell(title, nav, body, lang=lang_from_qs(qs), active_path=target, breadcrumb=title).encode(
                    "utf-8"
                ),
                "text/html; charset=utf-8",
            )

        # Clients directory (admin) — distinct from Portfolio operations
        if path in {"/clients", "/api/clients"}:
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            rows = build_portfolio(
                actor_tenant_ids=actor_tenants,
                is_superuser=is_super,
                registry_path=_active_registry(),
            )
            nav = _nav_qs(qs)
            if path == "/clients":
                return self._send(
                    200,
                    product_pages.clients_page(
                        rows,
                        load_assignments(),
                        nav,
                        q=qs.get("q", [""])[0],
                        status=qs.get("status", [""])[0],
                        framework=qs.get("framework", [""])[0],
                    ).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
            return self._send(
                200,
                json.dumps(to_jsonable(rows), ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

        # Framework Knowledge Base
        if path in {"/frameworks", "/api/frameworks", "/frameworks/detail", "/api/frameworks/detail"}:
            auth = self._gate(qs, permission=PERM_KB_READ)
            if auth is None:
                return
            actor_tenants, is_super = auth
            programs = [
                p
                for p, _ in load_portfolio_programs(_active_registry())
                if is_super
                or assert_tenant_access(
                    actor_tenant_ids=actor_tenants,
                    is_superuser=is_super,
                    target_tenant_id=p.tenant_id,
                ).allowed
            ]
            ctx = authoring_routes.frameworks_list_context(programs)
            versions = ctx["versions"]
            usage = ctx["usage"]
            nav = _nav_qs(qs)
            if path in {"/frameworks", "/api/frameworks"} and "framework_id" not in qs:
                if path == "/frameworks":
                    return self._send(
                        200,
                        product_pages.frameworks_page(
                            versions,
                            usage,
                            nav,
                            meta_by_id=ctx["meta_by_id"],
                            coverage_by_fw=ctx["coverage_by_fw"],
                        ).encode("utf-8"),
                        "text/html; charset=utf-8",
                    )
                return self._send(
                    200,
                    json.dumps(
                        {"versions": to_jsonable(versions), "usage": usage},
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    "application/json",
                )
            fw_id = qs.get("framework_id", [""])[0]
            vers = fw_versions.list_versions(framework_id=fw_id) if fw_id else versions
            selected = qs.get("version_id", [None])[0]
            clients = [
                p.tenant_name
                for p in programs
                if any(r.framework_id == fw_id for r in p.requirements)
            ]
            if path.startswith("/api/"):
                return self._send(
                    200,
                    json.dumps(
                        {"versions": to_jsonable(vers), "clients": clients},
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    "application/json",
                )
            selected_ver = next((v for v in vers if v.id == selected), vers[0] if vers else None)
            maps = []
            coverage = {}
            if selected_ver:
                maps = kb_mappings.list_mappings(
                    framework_id=selected_ver.framework_id,
                    framework_version=selected_ver.version,
                )
                coverage = kb_mappings.coverage_summary(selected_ver.requirements, maps)
            return self._send(
                200,
                product_pages.framework_detail_page(
                    vers,
                    selected_id=selected,
                    nav_qs=nav,
                    usage_clients=clients,
                    tab=qs.get("tab", ["overview"])[0],
                    meta=framework_registry.get_framework(fw_id),
                    mappings=maps,
                    coverage=coverage,
                ).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/api/frameworks/clone":
            auth = self._gate(qs, permission=PERM_KB_WRITE)
            if auth is None:
                return
            vid = qs.get("version_id", [""])[0]
            new_ver = qs.get("new_version", [""])[0]
            if not vid or not new_ver:
                return self._deny(400, "version_id_and_new_version_required")
            try:
                draft = fw_versions.clone_draft(vid, new_version=new_ver)
            except KeyError:
                return self._deny(404, "version_not_found")
            ctx = getattr(self, "_auth_ctx", None)
            audit_mod.record_event(
                actor_user_id=(ctx.username if ctx else "unknown") or "unknown",
                action=audit_mod.FRAMEWORK_VERSION_CLONE,
                entity_type="FrameworkVersion",
                entity_id=draft.id,
                new_value={"version": draft.version, "cloned_from": vid},
            )
            return self._send(
                200,
                json.dumps(to_jsonable(draft), ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

        if path == "/api/frameworks/publish":
            auth = self._gate(qs, permission=PERM_FRAMEWORK_PUBLISH)
            if auth is None:
                return
            vid = qs.get("version_id", [""])[0]
            try:
                pub = fw_versions.publish_version(vid)
            except KeyError:
                return self._deny(404, "version_not_found")
            ctx = getattr(self, "_auth_ctx", None)
            audit_mod.record_event(
                actor_user_id=(ctx.username if ctx else "unknown") or "unknown",
                action=audit_mod.FRAMEWORK_VERSION_PUBLISHED,
                entity_type="FrameworkVersion",
                entity_id=pub.id,
                new_value={"version": pub.version, "status": pub.status},
            )
            return self._send(
                200,
                json.dumps(to_jsonable(pub), ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

        if path == "/api/frameworks/patch":
            auth = self._gate(qs, permission=PERM_KB_WRITE)
            if auth is None:
                return
            vid = qs.get("version_id", [""])[0]
            # Intentionally no body patch via GET — deny published via service
            try:
                fw_versions.update_published_denied(vid, {"notes": "denied_probe"})
            except fw_versions.ImmutabilityError:
                return self._deny(403, "published_version_immutable")
            except KeyError:
                return self._deny(404, "version_not_found")
            return self._deny(400, "use_clone_workflow")

        # Mapping management (KB editor; optional program overlay)
        if path in {"/mappings", "/api/mappings"}:
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            programs = [
                p
                for p, _ in load_portfolio_programs(_active_registry())
                if is_super
                or assert_tenant_access(
                    actor_tenant_ids=actor_tenants,
                    is_superuser=is_super,
                    target_tenant_id=p.tenant_id,
                ).allowed
            ]
            authoring_routes.seed_kb(programs)
            program = _resolve_program(qs)
            relation = qs.get("relation", [""])[0].upper()
            review = qs.get("review", [""])[0].upper()
            if program is not None:
                decision = assert_tenant_access(
                    actor_tenant_ids=actor_tenants,
                    is_superuser=is_super,
                    target_tenant_id=program.tenant_id,
                )
                if not decision.allowed:
                    return self._deny(403, decision.reason)
                checklist = build_unified_checklist(program)
                mappings = list(program.mappings)
                unmapped = checklist.unmapped
                nav = _nav_qs(
                    qs,
                    program_id=program.program_id,
                    tenant_name=program.tenant_name,
                    program_name=program.program_name,
                )
            else:
                mappings = kb_mappings.list_mappings()
                # Unmapped across all draft+published versions
                mapped_ids = {m.requirement_id for m in mappings}
                unmapped = []
                for v in fw_versions.list_versions():
                    for r in v.requirements:
                        if getattr(r, "is_leaf", True) and r.id not in mapped_ids:
                            unmapped.append(
                                type(
                                    "U",
                                    (),
                                    {
                                        "id": r.id,
                                        "code": r.code,
                                        "title": r.title,
                                        "framework_name": v.framework_name,
                                        "framework_version": v.version,
                                    },
                                )()
                            )
                nav = _nav_qs(qs)
            if relation:
                mappings = [
                    m
                    for m in mappings
                    if (m.relation.value if hasattr(m.relation, "value") else m.relation)
                    == relation
                ]
            if review:
                mappings = [
                    m
                    for m in mappings
                    if (
                        m.review_status.value
                        if hasattr(m.review_status, "value")
                        else m.review_status
                    )
                    == review
                ]
            if qs.get("unmapped_only", [""])[0] == "1":
                mappings = []
            if path == "/mappings":
                return self._send(
                    200,
                    product_pages.mappings_page(
                        mappings,
                        unmapped,
                        nav,
                        filters={
                            "program_id": program.program_id if program else "",
                            "relation": relation,
                            "review": review,
                            "unmapped_only": qs.get("unmapped_only", [""])[0],
                        },
                    ).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
            return self._send(
                200,
                json.dumps(
                    {
                        "mappings": to_jsonable(mappings),
                        "unmapped": to_jsonable(unmapped),
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
                "application/json",
            )

        # Audit log
        if path in {"/audit", "/api/audit"}:
            auth = self._gate(qs, permission=PERM_AUDIT_READ)
            if auth is None:
                return
            events = audit_mod.list_events(
                tenant_id=qs.get("tenant_id", [""])[0] or None,
                actor_user_id=qs.get("actor", [""])[0] or None,
                action=qs.get("action", [""])[0] or None,
                date_from=qs.get("date_from", [""])[0] or None,
                date_to=qs.get("date_to", [""])[0] or None,
            )
            nav = _nav_qs(qs)
            if path == "/audit":
                return self._send(
                    200,
                    product_pages.audit_page(
                        events,
                        nav,
                        filters={
                            "tenant_id": qs.get("tenant_id", [""])[0],
                            "actor": qs.get("actor", [""])[0],
                            "action": qs.get("action", [""])[0],
                            "date_from": qs.get("date_from", [""])[0],
                            "date_to": qs.get("date_to", [""])[0],
                        },
                    ).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
            return self._send(
                200,
                json.dumps({"events": to_jsonable(events)}, ensure_ascii=False).encode(
                    "utf-8"
                ),
                "application/json",
            )

        # Settings
        if path in {"/settings", "/api/settings"}:
            auth = self._gate(qs)
            if auth is None:
                return
            nav = _nav_qs(qs)
            ai_settings = None
            programs = load_portfolio_programs(_active_registry())
            if programs:
                tid = programs[0][0].tenant_id
                ai_settings = _ai_service().tenant_settings(tid)
            if path == "/settings":
                return self._send(
                    200,
                    product_pages.settings_page(
                        nav_qs=nav,
                        ai_settings=ai_settings,
                        users=list_users(),
                        assignments=load_assignments(),
                        mfa_status={"supported": True},
                    ).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
            return self._send(
                200,
                json.dumps(
                    {
                        "users": [
                            {
                                "username": u.username,
                                "role": u.role,
                                "tenant_ids": u.tenant_ids,
                                "mfa_enabled": u.mfa_enabled,
                            }
                            for u in list_users()
                        ],
                        "assignments": load_assignments(),
                    },
                    ensure_ascii=False,
                ).encode("utf-8"),
                "application/json",
            )

        # Evidence binary download (authorized)
        if path.startswith("/api/evidence/") and path.endswith("/download"):
            auth = self._gate(qs, permission=PERM_EVIDENCE_DOWNLOAD)
            if auth is None:
                return
            actor_tenants, is_super = auth
            eid = path[len("/api/evidence/") : -len("/download")].strip("/")
            item = evidence_storage.get_evidence(eid)
            if item is None:
                return self._deny(404, "evidence_not_found")
            ctx = getattr(self, "_auth_ctx", None)
            if ctx is None:
                return self._deny(401, "authentication_required")
            try:
                data = evidence_storage.read_evidence_bytes(
                    item,
                    evidence_storage.AuthzContext(
                        username=ctx.username or "",
                        role=ctx.role,
                        actor_tenant_ids=actor_tenants,
                        is_superuser=is_super,
                    ),
                )
            except PermissionError as exc:
                return self._deny(403, str(exc))
            except FileNotFoundError:
                return self._deny(404, "evidence_file_missing")
            audit_mod.record_event(
                actor_user_id=ctx.username or "unknown",
                action=audit_mod.EVIDENCE_DOWNLOADED,
                entity_type="Evidence",
                entity_id=item.id,
                tenant_id=item.tenant_id,
                detail=item.filename,
            )
            return self._send(
                200,
                data,
                item.content_type or "application/octet-stream",
                extra_headers={
                    "Content-Disposition": f'attachment; filename="{item.filename}"',
                    "X-Content-Type-Options": "nosniff",
                },
            )

        # Report snapshot generate / history
        if path in {"/api/report/snapshot", "/report/history", "/api/report/history"}:
            auth = self._gate(qs, permission=PERM_REPORT_GENERATE)
            if auth is None:
                return
            actor_tenants, is_super = auth
            program = _resolve_program(qs)
            if program is None:
                return self._deny(404, "program_not_found")
            decision = assert_tenant_access(
                actor_tenant_ids=actor_tenants,
                is_superuser=is_super,
                target_tenant_id=program.tenant_id,
            )
            if not decision.allowed:
                return self._deny(403, decision.reason)
            ctx = getattr(self, "_auth_ctx", None)
            if path == "/api/report/snapshot":
                snap = report_snapshots.generate_snapshot(
                    program, generated_by=(ctx.username if ctx else "unknown") or "unknown"
                )
                audit_mod.record_event(
                    actor_user_id=(ctx.username if ctx else "unknown") or "unknown",
                    action=audit_mod.REPORT_GENERATED,
                    entity_type="ReportSnapshot",
                    entity_id=snap.id,
                    tenant_id=program.tenant_id,
                    new_value={
                        "assessment_date": snap.assessment_date,
                        "baselines": snap.framework_baselines,
                    },
                )
                return self._send(
                    200,
                    json.dumps(to_jsonable(snap), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )
            items = report_snapshots.list_snapshots(
                tenant_id=program.tenant_id, program_id=program.program_id
            )
            if path == "/api/report/history":
                return self._send(
                    200,
                    json.dumps({"snapshots": items}, ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )
            nav = _nav_qs(qs, program_id=program.program_id)
            rows_html = "".join(
                "<tr>"
                f"<td>{s.get('generated_at')}</td>"
                f"<td>{s.get('generated_by')}</td>"
                f"<td>{s.get('program_name')}</td>"
                f"<td>{', '.join(s.get('baselines') or [])}</td>"
                f"<td><a href='/api/report/snapshot/get?id={s.get('id')}'>Apri</a></td>"
                "</tr>"
                for s in items
            )
            body = (
                f"<h1>Cronologia report</h1><div class='panel'><table class='data-table'>"
                f"<thead><tr><th>GeneratedAt</th><th>GeneratedBy</th><th>Program</th>"
                f"<th>Baseline</th><th></th></tr></thead><tbody>{rows_html}</tbody></table></div>"
            )
            from engine.ui_shell import render_shell

            return self._send(
                200,
                render_shell(
                    "Cronologia report", nav, body, lang=lang_from_qs(qs), active_path="/report"
                ).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/api/report/snapshot/get":
            auth = self._gate(qs, permission=PERM_REPORT_GENERATE)
            if auth is None:
                return
            snap = report_snapshots.get_snapshot(qs.get("id", [""])[0])
            if snap is None:
                return self._deny(404, "snapshot_not_found")
            actor_tenants, is_super = auth
            decision = assert_tenant_access(
                actor_tenant_ids=actor_tenants,
                is_superuser=is_super,
                target_tenant_id=snap.tenant_id,
            )
            if not decision.allowed:
                return self._deny(403, decision.reason)
            return self._send(
                200,
                json.dumps(to_jsonable(snap), ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

        # Phase 4 — Regulatory Intelligence (engine store; not program-scoped)
        if path in {
            "/sources",
            "/api/sources",
            "/changes",
            "/api/changes",
            "/change",
            "/api/change",
            "/suggestions",
            "/api/suggestions",
            "/api/regulatory/check",
            "/api/regulatory/review",
            "/api/regulatory/impact",
        }:
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            store = _reg_store()
            nav = _nav_qs(qs)

            if path == "/sources":
                return self._send(
                    200,
                    reg_pages.sources_page(store.list_sources(), nav).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
            if path == "/api/sources":
                return self._send(
                    200,
                    json.dumps(
                        {"sources": to_jsonable(store.list_sources())}, ensure_ascii=False
                    ).encode("utf-8"),
                    "application/json",
                )
            if path == "/changes":
                return self._send(
                    200,
                    reg_pages.changes_page(store.list_changes(), nav).encode("utf-8"),
                    "text/html; charset=utf-8",
                )
            if path == "/api/changes":
                return self._send(
                    200,
                    json.dumps(
                        {"changes": to_jsonable(store.list_changes())}, ensure_ascii=False
                    ).encode("utf-8"),
                    "application/json",
                )
            if path == "/suggestions":
                return self._send(
                    200,
                    reg_pages.suggestions_page(store.list_suggestions(), nav).encode(
                        "utf-8"
                    ),
                    "text/html; charset=utf-8",
                )
            if path == "/api/suggestions":
                return self._send(
                    200,
                    json.dumps(
                        {"suggestions": to_jsonable(store.list_suggestions())},
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    "application/json",
                )
            if path in {"/change", "/api/change", "/api/regulatory/impact"}:
                change_id = qs.get("change_id", [""])[0]
                change = store.get_change(change_id)
                if change is None:
                    return self._deny(404, "change_not_found")
                impact = impact_for_change(
                    change_id,
                    store,
                    actor_tenant_ids=actor_tenants,
                    is_superuser=is_super,
                    registry_path=_active_registry(),
                )
                if path == "/change":
                    return self._send(
                        200,
                        reg_pages.change_detail_page(change, impact, nav).encode("utf-8"),
                        "text/html; charset=utf-8",
                    )
                payload = {
                    "change": to_jsonable(change),
                    "impact": to_jsonable(impact),
                }
                return self._send(
                    200,
                    json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )
            if path == "/api/regulatory/check":
                source_id = qs.get("source_id", [""])[0]
                source = store.get_source(source_id)
                if source is None:
                    return self._deny(404, "source_not_found")
                result = check_source(source, store)
                return self._send(
                    200,
                    json.dumps(to_jsonable(result), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )
            if path == "/api/regulatory/review":
                change_id = qs.get("change_id", [""])[0]
                status_raw = qs.get("status", [""])[0].upper()
                try:
                    status = ChangeStatus(status_raw)
                except ValueError:
                    return self._deny(400, "invalid_status")
                try:
                    change = review_change(change_id, store, status=status)
                except KeyError:
                    return self._deny(404, "change_not_found")
                return self._send(
                    200,
                    json.dumps(to_jsonable(change), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )

        # Phase 6 — Automated Evidence (Prowler/fixture → SUPPORTING evidence; human review)
        if path in {
            "/connectors",
            "/api/auto-evidence/connectors",
            "/auto-evidence",
            "/api/auto-evidence",
            "/api/auto-evidence/ingest",
            "/api/auto-evidence/review",
            "/api/auto-evidence/counts",
        }:
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            auto = _auto_ev_service()
            nav = _nav_qs(qs)

            if path in {"/connectors", "/api/auto-evidence/connectors"}:
                items = auto.list_connectors(
                    actor_tenant_ids=actor_tenants, is_superuser=is_super
                )
                if path == "/connectors":
                    return self._send(
                        200,
                        auto_ev_pages.connectors_page(items, nav).encode("utf-8"),
                        "text/html; charset=utf-8",
                    )
                return self._send(
                    200,
                    json.dumps(
                        {"connectors": to_jsonable(items)}, ensure_ascii=False
                    ).encode("utf-8"),
                    "application/json",
                )

            if path in {"/auto-evidence", "/api/auto-evidence"}:
                items = auto.list_evidence(
                    actor_tenant_ids=actor_tenants, is_superuser=is_super
                )
                if path == "/auto-evidence":
                    return self._send(
                        200,
                        auto_ev_pages.evidence_page(items, nav).encode("utf-8"),
                        "text/html; charset=utf-8",
                    )
                return self._send(
                    200,
                    json.dumps(
                        {"evidence": to_jsonable(items)}, ensure_ascii=False
                    ).encode("utf-8"),
                    "application/json",
                )

            if path == "/api/auto-evidence/ingest":
                connector_id = qs.get("connector_id", [""])[0]
                if not connector_id:
                    return self._deny(400, "connector_id_required")
                program = None
                if qs.get("program", [None])[0] or qs.get("program_id", [None])[0]:
                    try:
                        program = _resolve_program(qs)
                    except Exception as exc:  # noqa: BLE001
                        return self._deny(404, f"program_not_found: {exc}")
                try:
                    result = auto.ingest_connector(
                        connector_id,
                        program=program,
                        actor_tenant_ids=actor_tenants,
                        is_superuser=is_super,
                    )
                except KeyError as exc:
                    return self._deny(404, str(exc))
                except PermissionError as exc:
                    return self._deny(403, str(exc))
                return self._send(
                    200,
                    json.dumps(to_jsonable(result), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )

            if path == "/api/auto-evidence/review":
                eid = qs.get("evidence_id", [""])[0]
                status_raw = qs.get("status", [""])[0].upper()
                try:
                    status = EvidenceReviewStatus(status_raw)
                except ValueError:
                    return self._deny(400, "invalid_status")
                try:
                    rec = auto.review_evidence(
                        eid,
                        status=status,
                        actor_tenant_ids=actor_tenants,
                        is_superuser=is_super,
                    )
                except KeyError:
                    return self._deny(404, "evidence_not_found")
                except PermissionError as exc:
                    return self._deny(403, str(exc))
                except ValueError as exc:
                    return self._deny(400, str(exc))
                return self._send(
                    200,
                    json.dumps(to_jsonable(rec), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )

            if path == "/api/auto-evidence/counts":
                try:
                    program = _resolve_program(qs)
                except Exception as exc:  # noqa: BLE001
                    return self._deny(404, f"program_not_found: {exc}")
                decision = assert_tenant_access(
                    actor_tenant_ids=actor_tenants,
                    is_superuser=is_super,
                    target_tenant_id=program.tenant_id,
                )
                if not decision.allowed:
                    return self._deny(403, decision.reason)
                counts = auto.project_evidence_counts(program)
                # Explicit: counts are advisory; implementation statuses untouched
                return self._send(
                    200,
                    json.dumps(
                        {
                            "tenant_id": program.tenant_id,
                            "program_id": program.program_id,
                            "approved_auto_evidence_by_control": counts,
                            "note": (
                                "Advisory counts only — does not mutate AppliedControl "
                                "status or framework readiness"
                            ),
                        },
                        ensure_ascii=False,
                    ).encode("utf-8"),
                    "application/json",
                )

        # Phase 5 — AI Assistance (suggest only; human review required)
        if path in {
            "/ai/suggestions",
            "/api/ai/suggestions",
            "/ai/settings",
            "/api/ai/settings",
            "/api/ai/mapping-suggest",
            "/api/ai/regulatory-summary",
            "/api/ai/impact-suggest",
            "/api/ai/gap-explain",
            "/api/ai/review",
        }:
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            ai = _ai_service()
            nav = _nav_qs(qs)

            if path in {"/ai/suggestions", "/api/ai/suggestions"}:
                items = ai.list_suggestions(
                    actor_tenant_ids=actor_tenants, is_superuser=is_super
                )
                if path == "/ai/suggestions":
                    return self._send(
                        200,
                        ai_pages.suggestions_page(items, nav).encode("utf-8"),
                        "text/html; charset=utf-8",
                    )
                return self._send(
                    200,
                    json.dumps(
                        {"suggestions": to_jsonable(items)}, ensure_ascii=False
                    ).encode("utf-8"),
                    "application/json",
                )

            if path in {"/ai/settings", "/api/ai/settings"}:
                tenant_id = qs.get("tenant_id", [""])[0]
                if not tenant_id:
                    return self._deny(400, "tenant_id_required")
                if not is_super:
                    decision = assert_tenant_access(
                        actor_tenant_ids=actor_tenants,
                        is_superuser=is_super,
                        target_tenant_id=tenant_id,
                    )
                    if not decision.allowed:
                        return self._deny(403, decision.reason)
                enabled_raw = qs.get("enabled", [None])[0]
                if enabled_raw is not None:
                    settings = ai.set_ai_processing(
                        tenant_id, enabled_raw.lower() in {"1", "true", "yes"}
                    )
                else:
                    settings = ai.tenant_settings(tenant_id)
                if path == "/ai/settings":
                    return self._send(
                        200,
                        ai_pages.settings_page(settings, nav).encode("utf-8"),
                        "text/html; charset=utf-8",
                    )
                return self._send(
                    200,
                    json.dumps(to_jsonable(settings), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )

            if path == "/api/ai/review":
                sid = qs.get("suggestion_id", [""])[0]
                status_raw = qs.get("status", [""])[0].upper()
                try:
                    status = SuggestionReviewStatus(status_raw)
                except ValueError:
                    return self._deny(400, "invalid_status")
                try:
                    sug = ai.review_suggestion(
                        sid,
                        status=status,
                        actor_tenant_ids=actor_tenants,
                        is_superuser=is_super,
                    )
                except KeyError:
                    return self._deny(404, "suggestion_not_found")
                except PermissionError as exc:
                    return self._deny(403, str(exc))
                except ValueError as exc:
                    return self._deny(400, str(exc))
                return self._send(
                    200,
                    json.dumps(to_jsonable(sug), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )

            # Suggest endpoints need a program or change context.
            # Explicit program only — never inject default Michele into another tenant's AI call.
            program = None
            program_err = ""
            if qs.get("program", [None])[0] or qs.get("program_id", [None])[0]:
                try:
                    program = _resolve_program(qs)
                except Exception as exc:  # noqa: BLE001
                    program_err = str(exc)

            if path in {
                "/api/ai/mapping-suggest",
                "/api/ai/gap-explain",
            }:
                if program is None and not program_err:
                    # Backward-compatible default only when caller omits program entirely
                    try:
                        program = _resolve_program(qs)
                    except Exception as exc:  # noqa: BLE001
                        program_err = str(exc)
                if program is None:
                    return self._deny(404, f"program_not_found: {program_err}")
                decision = assert_tenant_access(
                    actor_tenant_ids=actor_tenants,
                    is_superuser=is_super,
                    target_tenant_id=program.tenant_id,
                )
                if not decision.allowed:
                    return self._deny(403, decision.reason)
                req_id = qs.get("requirement_id", [""])[0]
                if not req_id:
                    return self._deny(400, "requirement_id_required")
                try:
                    if path == "/api/ai/mapping-suggest":
                        sug = ai.suggest_mapping(program, req_id)
                    else:
                        sug = ai.explain_gap(program, req_id)
                except AIProcessingDisabled as exc:
                    return self._deny(403, str(exc))
                except KeyError as exc:
                    return self._deny(404, str(exc))
                return self._send(
                    200,
                    json.dumps(to_jsonable(sug), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )

            if path in {"/api/ai/regulatory-summary", "/api/ai/impact-suggest"}:
                change_id = qs.get("change_id", [""])[0]
                if not change_id:
                    return self._deny(400, "change_id_required")
                tenant_id = qs.get("tenant_id", [""])[0]
                if not tenant_id and program is not None:
                    tenant_id = program.tenant_id
                if not tenant_id:
                    return self._deny(400, "tenant_id_required")
                if not is_super:
                    decision = assert_tenant_access(
                        actor_tenant_ids=actor_tenants,
                        is_superuser=is_super,
                        target_tenant_id=tenant_id,
                    )
                    if not decision.allowed:
                        return self._deny(403, decision.reason)
                # Drop mismatched program context (prevents cross-tenant req IDs in AI payload)
                if program is not None and program.tenant_id != tenant_id:
                    program = None
                try:
                    if path == "/api/ai/regulatory-summary":
                        sug = ai.summarize_regulatory_change(
                            change_id, tenant_id=tenant_id, program=program
                        )
                    else:
                        sug = ai.suggest_impact(
                            change_id,
                            tenant_id=tenant_id,
                            actor_tenant_ids=actor_tenants,
                            is_superuser=is_super,
                        )
                except AIProcessingDisabled as exc:
                    return self._deny(403, str(exc))
                except KeyError as exc:
                    return self._deny(404, str(exc))
                return self._send(
                    200,
                    json.dumps(to_jsonable(sug), ensure_ascii=False).encode("utf-8"),
                    "application/json",
                )

        # Program-scoped routes
        try:
            program = _resolve_program(qs)
        except Exception as exc:  # noqa: BLE001
            return self._deny(404, f"program_not_found: {exc}")

        if program is None:
            auth = self._gate(qs)
            if auth is None:
                return
            actor_tenants, is_super = auth
            nav = _nav_qs(qs)
            if path.startswith("/api/"):
                return self._deny(404, "program_not_found")

            # Program-scoped HTML without program_id: attach a default client so
            # sidebar navigation actually changes page content (not the same empty shell).
            if path in _PROGRAM_SCOPED_HTML:
                rows = build_portfolio(
                    actor_tenant_ids=actor_tenants,
                    is_superuser=is_super,
                    registry_path=_active_registry(),
                )
                if len(rows) == 1:
                    flat = {k: v[0] for k, v in qs.items() if v}
                    flat["program_id"] = rows[0].program_id
                    flat.setdefault("lang", lang_from_qs(qs))
                    return self._redirect(f"{path}?{urlencode(flat)}")
                if len(rows) > 1:
                    return self._send(
                        200,
                        _select_client_html(nav, rows, active_path=path),
                        "text/html; charset=utf-8",
                    )
                return self._send(
                    200,
                    _empty_workspace_html(nav, active_path=path),
                    "text/html; charset=utf-8",
                )

            return self._send(
                200,
                _empty_workspace_html(nav, active_path=path),
                "text/html; charset=utf-8",
            )

        auth = self._gate(qs, program.tenant_id)
        if auth is None:
            return

        nav = _nav_qs(qs, program_id=program.program_id)
        checklist = build_unified_checklist(program)
        readiness = framework_readiness(program, checklist)
        impact = rank_control_impact(program, checklist)

        if path in {"/checklist"}:
            body = _html_checklist(checklist, readiness, impact, nav).encode("utf-8")
            return self._send(200, body, "text/html; charset=utf-8")

        if path == "/api/unified-checklist":
            payload = {
                "checklist": to_jsonable(checklist),
                "readiness": to_jsonable(readiness),
                "impact": to_jsonable(impact),
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            return self._send(200, body, "application/json")

        if path == "/client":
            dash = build_client_dashboard(program)
            return self._send(
                200,
                ux_pages.client_page(dash, nav).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/api/client":
            dash = build_client_dashboard(program)
            return self._send(
                200,
                json.dumps(to_jsonable(dash), ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

        def _gap_filter_from_qs() -> GapFilter:
            return GapFilter(
                framework=qs.get("framework", [""])[0] or None,
                status=qs.get("status", [""])[0] or None,
                owner=qs.get("owner", [""])[0] or None,
                priority=qs.get("priority", [""])[0] or None,
                deadline_before=qs.get("deadline_before", [""])[0] or None,
                deadline_after=qs.get("deadline_after", [""])[0] or None,
                mapped=(
                    True
                    if qs.get("mapped", [""])[0] == "1"
                    else False
                    if qs.get("mapped", [""])[0] == "0"
                    else None
                ),
                missing_evidence=True if qs.get("missing_evidence", [""])[0] == "1" else None,
                search=qs.get("search", [""])[0] or None,
            )

        if path == "/gaps":
            flt = _gap_filter_from_qs()
            rows = filter_gap_rows(build_gap_rows(program, checklist), flt)
            filter_values = {
                "lang": lang_from_qs(qs),
                "superuser": "1" if qs.get("superuser", ["0"])[0] in {"1", "true", "yes"} else "",
                "actor_tenants": qs.get("actor_tenants", [""])[0],
                "program_id": program.program_id,
                "framework": qs.get("framework", [""])[0],
                "status": qs.get("status", [""])[0],
                "owner": qs.get("owner", [""])[0],
                "priority": qs.get("priority", [""])[0],
                "deadline_before": qs.get("deadline_before", [""])[0],
                "deadline_after": qs.get("deadline_after", [""])[0],
                "mapped": qs.get("mapped", [""])[0],
                "missing_evidence": qs.get("missing_evidence", [""])[0],
                "search": qs.get("search", [""])[0],
            }
            return self._send(
                200,
                ux_pages.gaps_page(rows, nav, filter_values).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/api/gaps":
            rows = filter_gap_rows(build_gap_rows(program, checklist), _gap_filter_from_qs())
            return self._send(
                200,
                json.dumps(to_jsonable(rows), ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

        if path == "/control":
            ref = qs.get("control_ref", [""])[0]
            detail = control_detail(program, ref, checklist)
            if detail is None:
                return self._deny(404, "control_not_found")
            return self._send(
                200,
                ux_pages.control_page(detail, nav).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/api/control":
            ref = qs.get("control_ref", [""])[0]
            detail = control_detail(program, ref, checklist)
            if detail is None:
                return self._deny(404, "control_not_found")
            return self._send(
                200,
                json.dumps(to_jsonable(detail), ensure_ascii=False).encode("utf-8"),
                "application/json",
            )

        if path == "/owners":
            return self._send(
                200,
                ux_pages.owners_page(owner_view(program, checklist), nav).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/deadlines":
            return self._send(
                200,
                ux_pages.deadlines_page(deadline_view(program, checklist), nav).encode(
                    "utf-8"
                ),
                "text/html; charset=utf-8",
            )

        if path == "/evidence":
            return self._send(
                200,
                ux_pages.evidence_page(evidence_view(program, checklist), nav).encode(
                    "utf-8"
                ),
                "text/html; charset=utf-8",
            )

        if path == "/tasks":
            return self._send(
                200,
                ux_pages.tasks_page(task_view(program, checklist), nav).encode("utf-8"),
                "text/html; charset=utf-8",
            )

        if path == "/report":
            body = report_html(program, nav_qs=nav).encode("utf-8")
            return self._send(200, body, "text/html; charset=utf-8")

        if path == "/report.csv":
            body = report_csv(program).encode("utf-8")
            return self._send(200, body, "text/csv; charset=utf-8")

        if path == "/api/owners":
            return self._send(
                200,
                json.dumps(to_jsonable(owner_view(program, checklist)), ensure_ascii=False).encode(),
                "application/json",
            )

        if path == "/api/deadlines":
            return self._send(
                200,
                json.dumps(
                    to_jsonable(deadline_view(program, checklist)), ensure_ascii=False
                ).encode(),
                "application/json",
            )

        if path == "/api/evidence":
            return self._send(
                200,
                json.dumps(
                    to_jsonable(evidence_view(program, checklist)), ensure_ascii=False
                ).encode(),
                "application/json",
            )

        if path == "/api/tasks":
            return self._send(
                200,
                json.dumps(to_jsonable(task_view(program, checklist)), ensure_ascii=False).encode(),
                "application/json",
            )

        return self._deny(404, "not found")

    def do_HEAD(self):  # noqa: N802
        """Support HEAD for proxies/health probes without 501."""
        self.do_GET()

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        # Authoring form posts
        if path.startswith(
            (
                "/frameworks/",
                "/controls/",
                "/mappings/",
                "/clients/",
                "/programs/",
                "/evidence/",
                "/tasks/",
            )
        ):
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(max(0, min(length, 2_000_000))).decode("utf-8", "replace")
            if path in {"/evidence/new", "/tasks/new"}:
                auth = self._gate(qs)
                if auth is None:
                    return
                form = parse_qs(raw, keep_blank_values=True)
                title = (form.get("title") or [""])[0].strip()
                program = _resolve_program(qs)
                if program is None or not title:
                    return self._deny(400, "program_and_title_required")
                snap_path = program_authoring.find_program_path(
                    program.program_id, _active_registry()
                )
                if snap_path is None:
                    return self._deny(404, "program_snapshot_not_writable")
                raw_json = json.loads(snap_path.read_text(encoding="utf-8"))
                ctx = getattr(self, "_auth_ctx", None)
                actor = (ctx.username if ctx else "unknown") or "unknown"
                if path == "/evidence/new":
                    eid = f"ev-{__import__('secrets').token_hex(4)}"
                    raw_json.setdefault("evidences", []).append(
                        {
                            "id": eid,
                            "title": title,
                            "filename": title,
                            "control_refs": [],
                            "status": "REVIEW_REQUIRED",
                            "valid_until": (form.get("due_date") or [None])[0] or None,
                            "notes": (form.get("notes") or [""])[0],
                        }
                    )
                    audit_mod.record_event(
                        actor_user_id=actor,
                        action=audit_mod.EVIDENCE_CREATED,
                        entity_type="Evidence",
                        entity_id=eid,
                        tenant_id=program.tenant_id,
                    )
                    target = f"/evidence?{_nav_qs(qs, program_id=program.program_id)}"
                else:
                    tid = f"task-{__import__('secrets').token_hex(4)}"
                    raw_json.setdefault("tasks", []).append(
                        {
                            "id": tid,
                            "title": title,
                            "control_ref": None,
                            "owner": (form.get("owner") or [None])[0] or None,
                            "status": "TODO",
                            "due_date": (form.get("due_date") or [None])[0] or None,
                            "priority": "MEDIUM",
                            "notes": (form.get("notes") or [""])[0],
                        }
                    )
                    audit_mod.record_event(
                        actor_user_id=actor,
                        action=audit_mod.TASK_CREATED,
                        entity_type="Task",
                        entity_id=tid,
                        tenant_id=program.tenant_id,
                    )
                    target = f"/tasks?{_nav_qs(qs, program_id=program.program_id)}"
                snap_path.write_text(
                    json.dumps(raw_json, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return self._redirect(target)
            if authoring_routes.handle_authoring_post(self, path, qs, raw):
                return

        # Control optimistic lock + N/A rationale
        if path == "/api/control/update":
            auth = self._gate(qs)
            if auth is None:
                return
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(max(0, min(length, 256_000))).decode("utf-8", "replace")
            ctype = (self.headers.get("Content-Type") or "").lower()
            payload: dict = {}
            if "application/json" in ctype or (raw.strip().startswith("{")):
                try:
                    payload = json.loads(raw) if raw.strip() else {}
                except json.JSONDecodeError:
                    return self._deny(400, "invalid_json")
            else:
                form = parse_qs(raw, keep_blank_values=True)
                payload = {k: (v[0] if v else "") for k, v in form.items()}
            from engine.control_locking import ConflictError, ControlPatch, apply_patch
            from engine.domain import ImplementationStatus

            program = _resolve_program(qs)
            if program is None:
                return self._deny(404, "program_not_found")
            actor_tenants, is_super = auth
            decision = assert_tenant_access(
                actor_tenant_ids=actor_tenants,
                is_superuser=is_super,
                target_tenant_id=program.tenant_id,
            )
            if not decision.allowed:
                return self._deny(403, decision.reason)
            control_id = str(payload.get("control_id") or "")
            expected = int(payload.get("expected_version") or 0)
            new_status = payload.get("status")
            na_rationale = str(payload.get("not_applicable_rationale") or "").strip()
            if new_status == ImplementationStatus.NOT_APPLICABLE.value and not na_rationale:
                return self._deny(400, "na_rationale_required")
            try:
                new_v = apply_patch(
                    ControlPatch(
                        program_id=program.program_id,
                        control_id=control_id,
                        expected_version=expected,
                        changes=payload,
                    )
                )
            except ConflictError as exc:
                return self._deny(409, exc.user_message_it)
            # Persist implementation fields onto program snapshot when available
            snap_path = program_authoring.find_program_path(
                program.program_id, _active_registry()
            )
            if snap_path is not None:
                try:
                    program_authoring.persist_control_changes(snap_path, control_id, payload)
                except KeyError:
                    pass
            ctx = getattr(self, "_auth_ctx", None)
            if new_status:
                audit_mod.record_event(
                    actor_user_id=(ctx.username if ctx else "unknown") or "unknown",
                    action=audit_mod.CONTROL_STATUS_CHANGED,
                    entity_type="ControlImplementation",
                    entity_id=control_id,
                    tenant_id=program.tenant_id,
                    old_value={"version": expected},
                    new_value={"status": new_status, "version": new_v},
                )
            # HTML form → redirect back to control detail
            if "application/json" not in ctype and not raw.strip().startswith("{"):
                return self._redirect(
                    f"/control?control_ref={control_id}&{_nav_qs(qs, program_id=program.program_id, tenant_name=program.tenant_name, program_name=program.program_name)}"
                )
            return self._send(
                200,
                json.dumps({"ok": True, "version": new_v}, ensure_ascii=False).encode(
                    "utf-8"
                ),
                "application/json",
            )

        if path != "/login":
            return self._deny(404, "not found")

        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(max(0, min(length, 64_000))).decode("utf-8", "replace")
        form = parse_qs(raw)
        username = (form.get("username") or form.get("email") or [""])[0].strip()
        password = (form.get("password") or [""])[0]
        mfa_code = (form.get("mfa_code") or [""])[0].strip()
        next_path = (form.get("next") or ["/portfolio"])[0] or "/portfolio"
        if not next_path.startswith("/") or next_path.startswith("//"):
            next_path = "/portfolio"
        lang = lang_from_qs(parse_qs(parsed.query))

        if not auth_configured() and not list_users():
            html = login_page_html(
                lang=lang or "it",
                error="Autenticazione non configurata sul server.",
                next_path=next_path,
            )
            return self._send(503, html.encode("utf-8"), "text/html; charset=utf-8")

        result = authenticate(username, password)
        if not result.ok or result.user is None:
            audit_mod.record_event(
                actor_user_id=username or "anonymous",
                action=audit_mod.LOGIN,
                entity_type="Session",
                entity_id="failed",
                detail="invalid_credentials",
            )
            html = login_page_html(
                lang=lang or "it",
                error="Credenziali non valide.",
                next_path=next_path,
            )
            return self._send(401, html.encode("utf-8"), "text/html; charset=utf-8")

        user = result.user
        mfa_ok = True
        if result.requires_mfa:
            if not mfa_code:
                html = login_page_html(
                    lang=lang or "it",
                    error="Inserisci il codice MFA.",
                    next_path=next_path,
                    mfa_pending=True,
                )
                return self._send(401, html.encode("utf-8"), "text/html; charset=utf-8")
            mfa_ok = verify_totp(user.mfa_secret or "", mfa_code)
            if not mfa_ok:
                html = login_page_html(
                    lang=lang or "it",
                    error="Codice MFA non valido.",
                    next_path=next_path,
                    mfa_pending=True,
                )
                return self._send(401, html.encode("utf-8"), "text/html; charset=utf-8")
        elif mfa_required_for_role(user.role) and not user.temporary_review:
            # Hook ready: enrollment recommended before real client data
            mfa_ok = True

        tenants = sorted(effective_tenant_ids(user))
        token = issue_session(
            user.username,
            role=user.role,
            tenant_ids=tenants,
            is_superuser=role_is_superuser(user.role_enum),
            mfa_verified=mfa_ok,
        )
        audit_mod.record_event(
            actor_user_id=user.username,
            action=audit_mod.LOGIN,
            entity_type="Session",
            entity_id=user.username,
            detail=(
                "TEMPORARY REVIEW CREDENTIAL"
                if user.temporary_review
                else f"role={user.role}"
            ),
        )
        return self._redirect(
            next_path,
            extra_headers={
                "Set-Cookie": session_cookie_header(
                    token, secure=self._request_is_secure()
                )
            },
        )

    def log_message(self, fmt, *args):  # noqa: A003
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main(argv: list[str] | None = None):
    import argparse

    parser = argparse.ArgumentParser(description="WayFold Compliance consultant HTTP API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8092)
    args = parser.parse_args(argv)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"WayFold Compliance listening on http://{args.host}:{args.port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

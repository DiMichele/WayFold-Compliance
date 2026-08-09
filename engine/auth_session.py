"""Consultant session auth for WayFold Compliance engine.

Signed cookie sessions with role + tenant membership.
Idle timeout via sliding last_activity; absolute timeout from issued_at.
Query-param auth is opt-in (dev/tests only).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from html import escape
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import quote

from engine.rbac import Role, parse_role, role_is_superuser

COOKIE_NAME = "wf_session"
# Absolute session lifetime
SESSION_ABSOLUTE_TTL_SEC = 60 * 60 * 8  # 8h
# Idle timeout (sliding)
SESSION_IDLE_TTL_SEC = 60 * 45  # 45 minutes
# Back-compat alias
SESSION_TTL_SEC = SESSION_ABSOLUTE_TTL_SEC


@dataclass(frozen=True)
class Session:
    username: str
    is_superuser: bool
    expires_at: int
    role: str = Role.CONSULTANT.value
    tenant_ids: tuple[str, ...] = ()
    issued_at: int = 0
    last_activity: int = 0
    mfa_verified: bool = True

    @property
    def role_enum(self) -> Role:
        return parse_role(self.role)


def open_access_enabled() -> bool:
    return os.environ.get("WAYFOLD_OPEN_ACCESS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def qs_auth_allowed() -> bool:
    """Allow ?superuser=1 / actor_tenants in query string (local/tests)."""
    raw = os.environ.get("WAYFOLD_ALLOW_QS_AUTH")
    if raw is not None and str(raw).strip():
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}
    from engine.runtime_paths import seed_demo_enabled

    return open_access_enabled() or seed_demo_enabled()


def auth_configured() -> bool:
    user = os.environ.get("WAYFOLD_AUTH_USER", "").strip()
    password = os.environ.get("WAYFOLD_AUTH_PASSWORD", "").strip()
    return bool(user and password)


def _session_secret() -> bytes:
    raw = os.environ.get("WAYFOLD_SESSION_SECRET", "").strip()
    if not raw:
        raw = "wayfold-dev-session-secret-not-for-production"
    return raw.encode("utf-8")


def issue_session(
    username: str,
    *,
    is_superuser: bool | None = None,
    role: str | Role = Role.SUPER_ADMIN,
    tenant_ids: list[str] | tuple[str, ...] | None = None,
    mfa_verified: bool = True,
) -> str:
    now = int(time.time())
    role_s = role.value if isinstance(role, Role) else parse_role(role).value
    if is_superuser is None:
        is_superuser = role_is_superuser(parse_role(role_s))
    tenants = ",".join(sorted({t for t in (tenant_ids or []) if t}))
    exp = now + SESSION_ABSOLUTE_TTL_SEC
    # username|super|exp|role|tenants|issued|last|mfa
    payload = (
        f"{username}|{1 if is_superuser else 0}|{exp}|{role_s}|{tenants}|"
        f"{now}|{now}|{1 if mfa_verified else 0}"
    )
    sig = hmac.new(_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def refresh_session(session: Session) -> str:
    """Sliding idle refresh — keeps issued_at, updates last_activity."""
    now = int(time.time())
    absolute_end = (session.issued_at or now) + SESSION_ABSOLUTE_TTL_SEC
    exp = min(now + SESSION_IDLE_TTL_SEC, absolute_end)
    tenants = ",".join(session.tenant_ids)
    payload = (
        f"{session.username}|{1 if session.is_superuser else 0}|{exp}|{session.role}|"
        f"{tenants}|{session.issued_at or now}|{now}|{1 if session.mfa_verified else 0}"
    )
    sig = hmac.new(_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def parse_session_token(token: str | None) -> Session | None:
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    expected = hmac.new(_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    parts = payload.split("|")
    # Legacy: username|super|exp
    if len(parts) == 3:
        username, super_flag, exp_s = parts
        try:
            exp = int(exp_s)
        except ValueError:
            return None
        now = int(time.time())
        if exp < now or not username:
            return None
        return Session(
            username=username,
            is_superuser=super_flag == "1",
            expires_at=exp,
            role=Role.SUPER_ADMIN.value if super_flag == "1" else Role.VIEWER.value,
            tenant_ids=(),
            issued_at=now,
            last_activity=now,
            mfa_verified=True,
        )
    if len(parts) != 8:
        return None
    username, super_flag, exp_s, role, tenants_s, issued_s, last_s, mfa_s = parts
    try:
        exp = int(exp_s)
        issued = int(issued_s)
        last = int(last_s)
    except ValueError:
        return None
    now = int(time.time())
    if not username:
        return None
    if exp < now:
        return None
    if issued and now - issued > SESSION_ABSOLUTE_TTL_SEC:
        return None
    if last and now - last > SESSION_IDLE_TTL_SEC:
        return None
    tenants = tuple(t for t in tenants_s.split(",") if t)
    return Session(
        username=username,
        is_superuser=super_flag == "1",
        expires_at=exp,
        role=parse_role(role).value,
        tenant_ids=tenants,
        issued_at=issued,
        last_activity=last,
        mfa_verified=mfa_s == "1",
    )


def session_from_cookie_header(cookie_header: str | None) -> Session | None:
    if not cookie_header:
        return None
    jar = SimpleCookie()
    try:
        jar.load(cookie_header)
    except Exception:  # noqa: BLE001
        return None
    morsel = jar.get(COOKIE_NAME)
    if morsel is None:
        return None
    return parse_session_token(morsel.value)


def verify_credentials(username: str, password: str) -> bool:
    """Backward-compatible env check. Prefer engine.users.authenticate."""
    from engine.users import authenticate

    return authenticate(username, password).ok


def session_cookie_header(token: str, *, secure: bool = True) -> str:
    parts = [
        f"{COOKIE_NAME}={token}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        f"Max-Age={SESSION_ABSOLUTE_TTL_SEC}",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def clear_session_cookie_header(*, secure: bool = True) -> str:
    parts = [
        f"{COOKIE_NAME}=",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        "Max-Age=0",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def login_page_html(
    *,
    lang: str = "it",
    error: str = "",
    next_path: str = "/portfolio",
    mfa_pending: bool = False,
) -> str:
    err = (
        f'<p class="login-error" role="alert">{escape(error)}</p>'
        if error
        else ""
    )
    title = "Accedi" if lang != "en" else "Sign in"
    subtitle = (
        "WayFold Compliance — accesso sicuro"
        if lang != "en"
        else "WayFold Compliance — secure access"
    )
    user_label = "Nome utente / Email" if lang != "en" else "Username / Email"
    pass_label = "Password"
    submit = "Accedi" if lang != "en" else "Sign in"
    mfa_field = ""
    if mfa_pending:
        mfa_label = "Codice MFA" if lang != "en" else "MFA code"
        mfa_field = f"""
  <label for="mfa_code">{escape(mfa_label)}</label>
  <input id="mfa_code" name="mfa_code" type="text" inputmode="numeric" autocomplete="one-time-code" required>
"""
    return f"""<!doctype html>
<html lang="{escape(lang)}"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{escape(title)} — WayFold Compliance</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--wf-bg:#f5f7fb;--wf-surface:#fff;--wf-ink:#151b2b;--wf-muted:#6f7a8e;--wf-border:#e2e7ef;--wf-primary:#675cf2;--wf-danger:#b42318;--wf-danger-soft:#fff0ef}}
*{{box-sizing:border-box}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;font-family:Inter,system-ui,sans-serif;background:
  radial-gradient(circle at 20% 0%,rgba(103,92,242,.12),transparent 40%),
  radial-gradient(circle at 90% 100%,rgba(16,21,34,.06),transparent 45%),
  var(--wf-bg);color:var(--wf-ink)}}
.card{{width:min(400px,92vw);background:var(--wf-surface);border:1px solid var(--wf-border);border-radius:14px;padding:28px 24px;box-shadow:0 6px 20px rgba(21,27,43,.045)}}
.mark{{width:40px;height:40px;border-radius:11px;background:linear-gradient(145deg,#7a71ff,#5a4ff0);margin-bottom:14px}}
h1{{margin:0;font-size:22px;letter-spacing:-.02em}}
.sub{{color:var(--wf-muted);font-size:13px;margin:6px 0 18px}}
label{{display:block;font-size:11px;font-weight:700;color:var(--wf-muted);text-transform:uppercase;letter-spacing:.06em;margin:0 0 6px}}
input{{width:100%;height:40px;border:1px solid var(--wf-border);border-radius:9px;padding:0 12px;margin-bottom:12px;font:inherit}}
input:focus{{outline:0;border-color:#beb8ff;box-shadow:0 0 0 3px rgba(103,92,242,.08)}}
button{{width:100%;height:40px;border:0;border-radius:9px;background:var(--wf-primary);color:#fff;font-weight:700;cursor:pointer}}
button:hover{{filter:brightness(.96)}}
.login-error{{background:var(--wf-danger-soft);color:var(--wf-danger);padding:10px 12px;border-radius:8px;font-size:13px;margin:0 0 12px}}
</style>
</head><body>
<form class="card" method="post" action="/login" autocomplete="on">
  <div class="mark" aria-hidden="true"></div>
  <h1>WayFold Compliance</h1>
  <p class="sub">{escape(subtitle)}</p>
  {err}
  <input type="hidden" name="next" value="{escape(next_path)}">
  <label for="username">{escape(user_label)}</label>
  <input id="username" name="username" type="text" required autocomplete="username" autocapitalize="none" spellcheck="false">
  <label for="password">{escape(pass_label)}</label>
  <input id="password" name="password" type="password" required autocomplete="current-password">
  {mfa_field}
  <button type="submit">{escape(submit)}</button>
</form>
</body></html>"""


def forbidden_page_html(*, lang: str = "it") -> str:
    title = "Accesso non autorizzato" if lang != "en" else "Unauthorized"
    body = (
        "Non hai i permessi per visualizzare questa risorsa."
        if lang != "en"
        else "You do not have permission to view this resource."
    )
    return f"""<!doctype html>
<html lang="{escape(lang)}"><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>body{{font-family:Inter,system-ui,sans-serif;display:grid;place-items:center;min-height:100vh;background:#f5f7fb;color:#151b2b}}
.card{{max-width:420px;padding:28px;border:1px solid #e2e7ef;border-radius:14px;background:#fff}}
h1{{margin:0 0 8px;font-size:22px}}p{{color:#6f7a8e}}a{{color:#675cf2}}</style></head>
<body><div class="card"><h1>{escape(title)}</h1><p>{escape(body)}</p>
<p><a href="/portfolio">Torna al portfolio</a></p></div></body></html>"""


def wants_html(accept: str | None, path: str) -> bool:
    if path.startswith("/api/"):
        return False
    if not accept:
        return True
    a = accept.lower()
    if "application/json" in a and "text/html" not in a:
        return False
    return True

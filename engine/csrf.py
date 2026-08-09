"""CSRF protection for cookie-session browser mutations."""

from __future__ import annotations

import hmac
import secrets
from http.cookies import SimpleCookie
from urllib.parse import urlparse

CSRF_COOKIE = "wf_csrf"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"


def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_cookie_header(token: str, *, secure: bool = True) -> str:
    parts = [
        f"{CSRF_COOKIE}={token}",
        "Path=/",
        "SameSite=Lax",
        "Max-Age=28800",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def csrf_token_from_cookie_header(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    jar = SimpleCookie()
    try:
        jar.load(cookie_header)
    except Exception:  # noqa: BLE001
        return None
    morsel = jar.get(CSRF_COOKIE)
    return morsel.value if morsel else None


def validate_csrf(
    *,
    method: str,
    cookie_token: str | None,
    form_token: str | None,
    header_token: str | None,
    origin: str | None,
    referer: str | None,
    host: str | None,
) -> str | None:
    """Return error code or None if OK. Safe methods skip token check."""
    m = method.upper()
    if m in {"GET", "HEAD", "OPTIONS"}:
        return None

    presented = (header_token or form_token or "").strip()
    cookie = (cookie_token or "").strip()
    if not cookie or not presented:
        return "csrf_missing"
    if not hmac.compare_digest(cookie, presented):
        return "csrf_invalid"

    origin_err = _check_same_origin(origin=origin, referer=referer, host=host)
    if origin_err:
        return origin_err
    return None


def _check_same_origin(
    *,
    origin: str | None,
    referer: str | None,
    host: str | None,
) -> str | None:
    host_l = (host or "").split(":")[0].lower()
    if origin:
        if origin == "null":
            return "csrf_bad_origin"
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"}:
            return "csrf_bad_origin"
        oh = (parsed.hostname or "").lower()
        if host_l and oh and oh != host_l:
            return "csrf_bad_origin"
        return None
    if referer:
        parsed = urlparse(referer)
        rh = (parsed.hostname or "").lower()
        if host_l and rh and rh != host_l:
            return "csrf_bad_origin"
        return None
    # Token still required; Origin/Referer optional for same-host form posts.
    return None

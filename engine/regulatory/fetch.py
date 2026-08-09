from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# SSRF hardening for regulatory watcher HTTP fetches
DEFAULT_TIMEOUT_SEC = 15
DEFAULT_MAX_BYTES = 2_000_000
BLOCKED_HOSTS = {
    "metadata.google.internal",
    "metadata",
    "metadata.goog",
    "169.254.169.254",
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}


@dataclass
class FetchResult:
    ok: bool
    url: str
    content: bytes = b""
    content_type: str = "text/plain"
    error: str | None = None
    metadata: dict | None = None


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _test_mode() -> bool:
    import os

    return os.environ.get("WAYFOLD_TEST_MODE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def validate_url(url: str, *, allow_file: bool | None = None) -> str | None:
    """Return error message if URL is not allowed; None if OK.

    Production default: HTTP/HTTPS only. file:// and fixture:// denied unless
    explicit TEST MODE (WAYFOLD_TEST_MODE=1) or allow_file=True for tests.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    test = _test_mode()
    if allow_file is None:
        allow_file = test
    if scheme == "fixture":
        return None if test else "fixture_scheme_disabled"
    if scheme == "file":
        return None if allow_file else "file_scheme_disabled"
    if scheme in {"gopher", "ftp", "dict", "jar", "data"}:
        return f"unsupported_scheme:{scheme}"
    if scheme not in {"http", "https"}:
        return f"unsupported_scheme:{scheme or 'none'}"
    host = (parsed.hostname or "").lower()
    if not host:
        return "missing_host"
    if host in BLOCKED_HOSTS or host.endswith(".local"):
        return "blocked_host"
    try:
        # Literal IP in hostname
        ip = ipaddress.ip_address(host)
        if _is_blocked_ip(ip):
            return "private_or_reserved_ip"
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if _is_blocked_ip(ip):
                return "private_or_reserved_ip"
    except (socket.gaierror, ValueError, OSError):
        # DNS failure checked at fetch time
        pass
    return None


def fetch_url(
    url: str,
    *,
    fixture_root: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    max_bytes: int = DEFAULT_MAX_BYTES,
    allow_file: bool = True,
) -> FetchResult:
    err = validate_url(url, allow_file=allow_file)
    if err:
        return FetchResult(False, url, error=err)

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme == "fixture":
        return _fetch_fixture(url, fixture_root=fixture_root, max_bytes=max_bytes)
    if scheme == "file":
        path = Path(urlparse(url).path)
        # Windows: file:///C:/... → path may start with /
        if path.as_posix().startswith("/") and len(path.parts) > 1 and ":" in path.parts[1]:
            path = Path(*path.parts[1:])
        return _read_path(url, path, max_bytes=max_bytes, content_type=_guess_type(path))

    try:
        req = Request(url, headers={"User-Agent": "WayFoldRegulatoryEngine/0.1"})
        # Do not follow redirects automatically — block open-redirect SSRF.
        import urllib.request as _ur

        class _NoRedirect(_ur.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802
                return None

        opener = _ur.build_opener(_NoRedirect)
        with opener.open(req, timeout=timeout) as resp:  # noqa: S310 — URL validated above
            final = resp.geturl()
            raw = resp.read(max_bytes + 1)
            if len(raw) > max_bytes:
                return FetchResult(False, url, error="response_too_large")
            ctype = resp.headers.get_content_type() or "application/octet-stream"
            return FetchResult(
                True,
                url,
                content=raw,
                content_type=ctype,
                metadata={"status": getattr(resp, "status", 200), "final_url": final},
            )
    except HTTPError as exc:
        if 300 <= int(exc.code) < 400:
            location = exc.headers.get("Location") if exc.headers else None
            if location:
                redir_err = validate_url(location, allow_file=False)
                if redir_err:
                    return FetchResult(False, url, error=f"redirect_blocked:{redir_err}")
                # Re-validate DNS of redirect target without fetching again here
                return FetchResult(False, url, error="redirect_not_followed")
            return FetchResult(False, url, error=f"http_{exc.code}")
        return FetchResult(False, url, error=f"http_{exc.code}")
    except URLError as exc:
        return FetchResult(False, url, error=f"url_error:{exc.reason}")
    except TimeoutError:
        return FetchResult(False, url, error="timeout")
    except Exception as exc:  # noqa: BLE001
        return FetchResult(False, url, error=f"fetch_failed:{type(exc).__name__}")


def _fetch_fixture(url: str, *, fixture_root: Path | None, max_bytes: int) -> FetchResult:
    # fixture://demo-nis2/v1.html → <fixture_root>/demo-nis2/v1.html
    parsed = urlparse(url)
    rel = f"{parsed.netloc}{parsed.path}".lstrip("/")
    if not fixture_root:
        return FetchResult(False, url, error="fixture_root_missing")
    path = (fixture_root / rel).resolve()
    try:
        path.relative_to(fixture_root.resolve())
    except ValueError:
        return FetchResult(False, url, error="fixture_path_escape")
    return _read_path(url, path, max_bytes=max_bytes, content_type=_guess_type(path))


def _read_path(url: str, path: Path, *, max_bytes: int, content_type: str) -> FetchResult:
    if not path.is_file():
        return FetchResult(False, url, error="file_not_found")
    data = path.read_bytes()
    if len(data) > max_bytes:
        return FetchResult(False, url, error="response_too_large")
    return FetchResult(
        True,
        url,
        content=data,
        content_type=content_type,
        metadata={"adapter": "file", "path": str(path)},
    )


def _guess_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return "text/html"
    if suffix == ".json":
        return "application/json"
    if suffix == ".pdf":
        return "application/pdf"
    return "text/plain"

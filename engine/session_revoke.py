"""Server-side session revocation / version bump.

Invalidates sessions on logout, password change, role change, tenant assignment change.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from engine.runtime_paths import data_root

_LOCK = threading.Lock()
# In-memory denylist of token signatures (or full tokens) + per-user min issued_at
_REVOKED_SIGS: set[str] = set()
_USER_MIN_ISSUED: dict[str, int] = {}


def _store_path() -> Path:
    return data_root() / "session_revoke.json"


def _load() -> None:
    path = _store_path()
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    with _LOCK:
        _REVOKED_SIGS.update(str(s) for s in data.get("revoked_sigs") or [])
        for u, ts in (data.get("user_min_issued") or {}).items():
            try:
                _USER_MIN_ISSUED[str(u).lower()] = int(ts)
            except (TypeError, ValueError):
                continue


def _save() -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        payload = {
            "revoked_sigs": sorted(_REVOKED_SIGS)[-5000:],
            "user_min_issued": dict(_USER_MIN_ISSUED),
        }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


_load()


def revoke_token(token: str) -> None:
    if not token or "." not in token:
        return
    sig = token.rsplit(".", 1)[-1]
    with _LOCK:
        _REVOKED_SIGS.add(sig)
    _save()


def bump_user_sessions(username: str) -> None:
    """Invalidate all sessions for user issued before now (password/role/tenant change)."""
    now = int(time.time())
    with _LOCK:
        _USER_MIN_ISSUED[username.strip().lower()] = now
    _save()


def is_token_revoked(token: str, *, username: str, issued_at: int) -> bool:
    if not token or "." not in token:
        return True
    sig = token.rsplit(".", 1)[-1]
    with _LOCK:
        if sig in _REVOKED_SIGS:
            return True
        min_issued = _USER_MIN_ISSUED.get(username.strip().lower(), 0)
        if issued_at and min_issued and issued_at < min_issued:
            return True
    return False


def reset_for_tests() -> None:
    with _LOCK:
        _REVOKED_SIGS.clear()
        _USER_MIN_ISSUED.clear()
    path = _store_path()
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass

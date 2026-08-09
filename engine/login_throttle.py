"""Login rate limiting by IP + username with backoff. Never logs passwords."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

_LOCK = threading.Lock()
_ATTEMPTS: dict[str, list[float]] = {}

# Window and thresholds
WINDOW_SEC = 900  # 15 minutes
MAX_ATTEMPTS = 8
BASE_BACKOFF_SEC = 2
MAX_BACKOFF_SEC = 300


@dataclass
class ThrottleDecision:
    allowed: bool
    retry_after_sec: int = 0
    reason: str = ""


def _key(ip: str, username: str) -> str:
    return f"{(ip or 'unknown').strip().lower()}|{(username or '').strip().lower()}"


def _prune(now: float, stamps: list[float]) -> list[float]:
    cutoff = now - WINDOW_SEC
    return [t for t in stamps if t >= cutoff]


def check_login_allowed(ip: str, username: str) -> ThrottleDecision:
    now = time.time()
    key = _key(ip, username)
    with _LOCK:
        stamps = _prune(now, _ATTEMPTS.get(key, []))
        _ATTEMPTS[key] = stamps
        if len(stamps) < MAX_ATTEMPTS:
            return ThrottleDecision(True)
        # Exponential-ish backoff based on surplus failures
        surplus = len(stamps) - MAX_ATTEMPTS + 1
        delay = min(MAX_BACKOFF_SEC, BASE_BACKOFF_SEC * (2 ** min(surplus, 8)))
        oldest_block = stamps[-MAX_ATTEMPTS]
        elapsed = now - oldest_block
        if elapsed < delay:
            return ThrottleDecision(
                False,
                retry_after_sec=int(delay - elapsed) + 1,
                reason="rate_limited",
            )
        return ThrottleDecision(True)


def record_login_failure(ip: str, username: str) -> None:
    now = time.time()
    key = _key(ip, username)
    with _LOCK:
        stamps = _prune(now, _ATTEMPTS.get(key, []))
        stamps.append(now)
        _ATTEMPTS[key] = stamps


def record_login_success(ip: str, username: str) -> None:
    key = _key(ip, username)
    with _LOCK:
        _ATTEMPTS.pop(key, None)


def reset_for_tests() -> None:
    with _LOCK:
        _ATTEMPTS.clear()

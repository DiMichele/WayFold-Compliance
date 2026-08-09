"""TOTP MFA helpers (pure Python — no external dependency).

Required for SUPER_ADMIN and CONSULTANT before real client data.
Temporary review credential may operate without MFA enrollment.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Iterable


def generate_totp_secret(nbytes: int = 20) -> str:
    return base64.b32encode(secrets.token_bytes(nbytes)).decode("ascii").rstrip("=")


def _normalize_secret(secret: str) -> bytes:
    pad = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(secret.upper() + pad, casefold=True)


def totp(
    secret: str,
    *,
    for_time: int | None = None,
    step: int = 30,
    digits: int = 6,
) -> str:
    counter = int((for_time if for_time is not None else time.time()) // step)
    key = _normalize_secret(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def verify_totp(
    secret: str,
    code: str,
    *,
    window: int = 1,
    step: int = 30,
    digits: int = 6,
) -> bool:
    if not code or not secret:
        return False
    cleaned = re_sub_digits(code)
    if len(cleaned) != digits:
        return False
    now = int(time.time())
    for drift in range(-window, window + 1):
        expected = totp(secret, for_time=now + drift * step, step=step, digits=digits)
        if hmac.compare_digest(expected, cleaned):
            return True
    return False


def re_sub_digits(code: str) -> str:
    return "".join(ch for ch in code.strip() if ch.isdigit())


def provisioning_uri(secret: str, *, account: str, issuer: str = "WayFold Compliance") -> str:
    from urllib.parse import quote

    label = quote(f"{issuer}:{account}")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits=6&period=30"
    )


def generate_recovery_codes(n: int = 8) -> list[str]:
    return [secrets.token_hex(4) for _ in range(n)]


def hash_recovery_codes(codes: Iterable[str]) -> list[str]:
    return [hashlib.sha256(c.encode("utf-8")).hexdigest() for c in codes]


def verify_recovery_code(code: str, hashed: list[str]) -> tuple[bool, list[str]]:
    digest = hashlib.sha256(code.strip().encode("utf-8")).hexdigest()
    remaining = list(hashed)
    for i, h in enumerate(remaining):
        if hmac.compare_digest(h, digest):
            remaining.pop(i)
            return True, remaining
    return False, remaining


def mfa_required_for_role(role: str) -> bool:
    return role in {"SUPER_ADMIN", "CONSULTANT"}

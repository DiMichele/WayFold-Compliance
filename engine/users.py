"""User directory + consultant↔tenant assignments (engine overlay).

Passwords are stored as PBKDF2-HMAC-SHA256 hashes. Temporary review credential
(admin/admin via env) remains supported as SUPER_ADMIN without being hardcoded.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from engine.rbac import Role, parse_role, role_is_superuser
from engine.runtime_paths import data_root

_PBKDF2_ITERATIONS = 210_000
_SALT_BYTES = 16


@dataclass
class UserRecord:
    username: str
    password_hash: str
    role: str
    tenant_ids: list[str] = field(default_factory=list)
    display_name: str = ""
    mfa_secret: str | None = None
    mfa_enabled: bool = False
    active: bool = True
    # Temporary review credential marker (env-backed admin)
    temporary_review: bool = False

    @property
    def role_enum(self) -> Role:
        return parse_role(self.role)


@dataclass
class AuthResult:
    ok: bool
    user: UserRecord | None = None
    reason: str = ""
    requires_mfa: bool = False


def users_path() -> Path:
    return data_root() / "users.json"


def assignments_path() -> Path:
    return data_root() / "consultant_assignments.json"


def _hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iters_s, salt_hex, digest_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    try:
        iters = int(iters_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(digest, expected)


def _load_raw() -> dict[str, Any]:
    path = users_path()
    if not path.is_file():
        return {"users": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"users": []}


def _save_raw(data: dict[str, Any]) -> None:
    path = users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def list_users() -> list[UserRecord]:
    data = _load_raw()
    out: list[UserRecord] = []
    for row in data.get("users", []):
        out.append(
            UserRecord(
                username=str(row.get("username", "")),
                password_hash=str(row.get("password_hash", "")),
                role=str(row.get("role", Role.VIEWER.value)),
                tenant_ids=list(row.get("tenant_ids") or []),
                display_name=str(row.get("display_name") or ""),
                mfa_secret=row.get("mfa_secret"),
                mfa_enabled=bool(row.get("mfa_enabled", False)),
                active=bool(row.get("active", True)),
                temporary_review=bool(row.get("temporary_review", False)),
            )
        )
    return [u for u in out if u.username]


def get_user(username: str) -> UserRecord | None:
    key = username.strip().lower()
    for u in list_users():
        if u.username.lower() == key:
            return u
    return None


def upsert_user(user: UserRecord) -> UserRecord:
    data = _load_raw()
    users = list(data.get("users") or [])
    found = False
    payload = asdict(user)
    for i, row in enumerate(users):
        if str(row.get("username", "")).lower() == user.username.lower():
            users[i] = payload
            found = True
            break
    if not found:
        users.append(payload)
    data["users"] = users
    _save_raw(data)
    return user


def create_user(
    username: str,
    password: str,
    *,
    role: Role | str,
    tenant_ids: list[str] | None = None,
    display_name: str = "",
) -> UserRecord:
    role_s = role.value if isinstance(role, Role) else str(role)
    rec = UserRecord(
        username=username.strip(),
        password_hash=_hash_password(password),
        role=role_s,
        tenant_ids=list(tenant_ids or []),
        display_name=display_name or username.strip(),
    )
    return upsert_user(rec)


def set_password(username: str, password: str) -> None:
    user = get_user(username)
    if user is None:
        raise KeyError(username)
    user.password_hash = _hash_password(password)
    upsert_user(user)


def load_assignments() -> dict[str, list[str]]:
    """username -> tenant_ids for consultants."""
    path = assignments_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, list[str]] = {}
    for row in raw.get("assignments", []):
        user = str(row.get("username", "")).strip().lower()
        tenants = [str(t) for t in (row.get("tenant_ids") or []) if t]
        if user:
            out[user] = tenants
    return out


def save_assignments(assignments: dict[str, list[str]]) -> None:
    path = assignments_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "assignments": [
            {"username": u, "tenant_ids": tids} for u, tids in sorted(assignments.items())
        ]
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def assign_consultant(username: str, tenant_ids: list[str]) -> None:
    data = load_assignments()
    data[username.strip().lower()] = list(tenant_ids)
    save_assignments(data)
    user = get_user(username)
    if user and user.role_enum == Role.CONSULTANT:
        user.tenant_ids = list(tenant_ids)
        upsert_user(user)


def effective_tenant_ids(user: UserRecord) -> set[str]:
    if role_is_superuser(user.role_enum):
        return set()
    assigned = load_assignments().get(user.username.lower())
    if assigned is not None:
        return set(assigned)
    return set(user.tenant_ids)


def authenticate(username: str, password: str) -> AuthResult:
    """Authenticate against user directory, then env temporary review credential."""
    user = get_user(username)
    if user is not None:
        if not user.active:
            return AuthResult(False, reason="user_inactive")
        if not verify_password(password, user.password_hash):
            return AuthResult(False, reason="invalid_credentials")
        return AuthResult(
            True,
            user=user,
            requires_mfa=bool(user.mfa_enabled and user.mfa_secret),
        )

    # Temporary review credential (env) — SUPER_ADMIN, never hardcoded in repo.
    expected_user = os.environ.get("WAYFOLD_AUTH_USER", "").strip()
    expected_pass = os.environ.get("WAYFOLD_AUTH_PASSWORD", "").strip()
    if (
        expected_user
        and expected_pass
        and secrets.compare_digest(username, expected_user)
        and secrets.compare_digest(password, expected_pass)
    ):
        return AuthResult(
            True,
            user=UserRecord(
                username=expected_user,
                password_hash="",
                role=Role.SUPER_ADMIN.value,
                tenant_ids=[],
                display_name=expected_user,
                temporary_review=True,
                mfa_enabled=False,
            ),
            requires_mfa=False,
        )
    return AuthResult(False, reason="invalid_credentials")


def seed_rbac_test_users(*, password: str | None = None) -> dict[str, UserRecord]:
    """Create deterministic fixture users for automated tests (not public passwords)."""
    pw = password or secrets.token_urlsafe(18)
    specs = [
        ("superadmin_test", Role.SUPER_ADMIN, []),
        ("consultant_test", Role.CONSULTANT, ["tenant-michele-demo"]),
        ("client_admin_michele", Role.CLIENT_ADMIN, ["tenant-michele-demo"]),
        ("client_member_michele", Role.CLIENT_MEMBER, ["tenant-michele-demo"]),
        ("viewer_michele", Role.VIEWER, ["tenant-michele-demo"]),
        ("client_admin_alfa", Role.CLIENT_ADMIN, ["tenant-alfa-demo"]),
    ]
    out: dict[str, UserRecord] = {}
    for username, role, tenants in specs:
        out[username] = create_user(
            username, pw, role=role, tenant_ids=tenants, display_name=username
        )
    assign_consultant("consultant_test", ["tenant-michele-demo"])
    return out

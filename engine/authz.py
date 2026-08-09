from __future__ import annotations

from dataclasses import dataclass, field

from engine.rbac import (
    Role,
    has_permission,
    parse_role,
    role_is_superuser,
)


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str


@dataclass
class AuthContext:
    """Authenticated request context for engine handlers."""

    username: str | None
    role: Role
    actor_tenant_ids: set[str] = field(default_factory=set)
    is_superuser: bool = False
    mfa_verified: bool = True
    temporary_review: bool = False

    def can(self, permission: str) -> bool:
        return has_permission(self.role, permission)


def assert_tenant_access(
    *,
    actor_tenant_ids: set[str],
    is_superuser: bool,
    target_tenant_id: str,
) -> AccessDecision:
    """Server-side tenant gate for WayFold Compliance endpoints/services.

    Overlays a hard tenant boundary before returning unified checklist /
    readiness / impact for a program.
    """
    if is_superuser:
        return AccessDecision(True, "superuser")
    if target_tenant_id in actor_tenant_ids:
        return AccessDecision(True, "tenant_member")
    return AccessDecision(False, "tenant_isolation_denied")


def assert_permission(ctx: AuthContext, permission: str) -> AccessDecision:
    if ctx.can(permission):
        return AccessDecision(True, "permission_granted")
    return AccessDecision(False, "permission_denied")


def assert_tenant_and_permission(
    ctx: AuthContext,
    *,
    target_tenant_id: str,
    permission: str,
) -> AccessDecision:
    perm = assert_permission(ctx, permission)
    if not perm.allowed:
        return perm
    return assert_tenant_access(
        actor_tenant_ids=ctx.actor_tenant_ids,
        is_superuser=ctx.is_superuser,
        target_tenant_id=target_tenant_id,
    )


def context_from_session_fields(
    *,
    username: str | None,
    role: str | Role,
    tenant_ids: set[str] | list[str] | tuple[str, ...],
    is_superuser: bool | None = None,
    mfa_verified: bool = True,
    temporary_review: bool = False,
) -> AuthContext:
    role_e = role if isinstance(role, Role) else parse_role(role)
    super_flag = role_is_superuser(role_e) if is_superuser is None else is_superuser
    return AuthContext(
        username=username,
        role=role_e,
        actor_tenant_ids=set(tenant_ids),
        is_superuser=super_flag,
        mfa_verified=mfa_verified,
        temporary_review=temporary_review,
    )

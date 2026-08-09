"""Role-based access control for WayFold Compliance engine.

Semantic roles (product language). Mapped onto session + tenant membership.
Does not duplicate CISO RoleAssignment; overlays the consultant engine.
"""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    CONSULTANT = "CONSULTANT"
    CLIENT_ADMIN = "CLIENT_ADMIN"
    CLIENT_MEMBER = "CLIENT_MEMBER"
    VIEWER = "VIEWER"


# Permission catalogue (engine surface)
PERM_KB_WRITE = "kb.write"
PERM_KB_READ = "kb.read"
PERM_MAPPING_WRITE = "mapping.write"
PERM_MAPPING_APPROVE = "mapping.approve"
PERM_CONTROL_WRITE = "control.write"
PERM_EVIDENCE_READ = "evidence.read"
PERM_EVIDENCE_WRITE = "evidence.write"
PERM_EVIDENCE_DOWNLOAD = "evidence.download"
PERM_TASK_WRITE = "task.write"
PERM_REPORT_GENERATE = "report.generate"
PERM_AUDIT_READ = "audit.read"
PERM_SETTINGS_WRITE = "settings.write"
PERM_AI_TOGGLE = "ai.toggle"
PERM_FRAMEWORK_PUBLISH = "framework.publish"
PERM_USER_ADMIN = "user.admin"
PERM_CLIENT_CREATE = "client.create"
PERM_PROGRAM_CREATE = "program.create"


_ROLE_PERMS: dict[Role, frozenset[str]] = {
    Role.SUPER_ADMIN: frozenset(
        {
            PERM_KB_WRITE,
            PERM_KB_READ,
            PERM_MAPPING_WRITE,
            PERM_MAPPING_APPROVE,
            PERM_CONTROL_WRITE,
            PERM_EVIDENCE_READ,
            PERM_EVIDENCE_WRITE,
            PERM_EVIDENCE_DOWNLOAD,
            PERM_TASK_WRITE,
            PERM_REPORT_GENERATE,
            PERM_AUDIT_READ,
            PERM_SETTINGS_WRITE,
            PERM_AI_TOGGLE,
            PERM_FRAMEWORK_PUBLISH,
            PERM_USER_ADMIN,
            PERM_CLIENT_CREATE,
            PERM_PROGRAM_CREATE,
        }
    ),
    Role.CONSULTANT: frozenset(
        {
            PERM_KB_READ,
            PERM_KB_WRITE,
            PERM_MAPPING_WRITE,
            PERM_MAPPING_APPROVE,
            PERM_CONTROL_WRITE,
            PERM_EVIDENCE_READ,
            PERM_EVIDENCE_WRITE,
            PERM_EVIDENCE_DOWNLOAD,
            PERM_TASK_WRITE,
            PERM_REPORT_GENERATE,
            PERM_AUDIT_READ,
            PERM_AI_TOGGLE,
            PERM_FRAMEWORK_PUBLISH,
            PERM_CLIENT_CREATE,
            PERM_PROGRAM_CREATE,
        }
    ),
    Role.CLIENT_ADMIN: frozenset(
        {
            PERM_KB_READ,
            PERM_CONTROL_WRITE,
            PERM_EVIDENCE_READ,
            PERM_EVIDENCE_WRITE,
            PERM_EVIDENCE_DOWNLOAD,
            PERM_TASK_WRITE,
            PERM_REPORT_GENERATE,
            PERM_AUDIT_READ,
            PERM_AI_TOGGLE,
        }
    ),
    Role.CLIENT_MEMBER: frozenset(
        {
            PERM_KB_READ,
            PERM_CONTROL_WRITE,
            PERM_EVIDENCE_READ,
            PERM_EVIDENCE_WRITE,
            PERM_EVIDENCE_DOWNLOAD,
            PERM_TASK_WRITE,
            PERM_REPORT_GENERATE,
        }
    ),
    Role.VIEWER: frozenset(
        {
            PERM_KB_READ,
            PERM_EVIDENCE_READ,
            PERM_EVIDENCE_DOWNLOAD,
            PERM_REPORT_GENERATE,
            PERM_AUDIT_READ,
        }
    ),
}


def parse_role(raw: str | None) -> Role:
    if not raw:
        return Role.VIEWER
    try:
        return Role(str(raw).strip().upper())
    except ValueError:
        return Role.VIEWER


def is_global_role(role: Role) -> bool:
    return role in {Role.SUPER_ADMIN, Role.CONSULTANT}


def role_is_superuser(role: Role) -> bool:
    """SUPER_ADMIN bypasses tenant filters. CONSULTANT does not (assignments apply)."""
    return role == Role.SUPER_ADMIN


def has_permission(role: Role | str, permission: str) -> bool:
    r = role if isinstance(role, Role) else parse_role(role)
    return permission in _ROLE_PERMS.get(r, frozenset())


def permissions_for(role: Role | str) -> frozenset[str]:
    r = role if isinstance(role, Role) else parse_role(role)
    return _ROLE_PERMS.get(r, frozenset())

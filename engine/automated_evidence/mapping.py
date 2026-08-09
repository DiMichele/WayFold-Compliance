from __future__ import annotations

from .domain import CheckControlMapping

# Default technical check → canonical control mappings for demo / fixtures.
# SUPPORTING only: a PASS never means the whole organizational requirement is compliant.
DEFAULT_CHECK_MAPPINGS: list[CheckControlMapping] = [
    CheckControlMapping(
        check_id="iam_root_mfa_enabled",
        canonical_control_ref="CTRL-IAM-001",
        relation="SUPPORTING",
        notes="Root MFA is a technical signal for privileged access — not full PAM program proof",
    ),
    CheckControlMapping(
        check_id="iam_user_mfa_enabled_console_access",
        canonical_control_ref="CTRL-IAM-001",
        relation="SUPPORTING",
        notes="Console MFA supports privileged access hygiene",
    ),
    CheckControlMapping(
        check_id="iam_password_policy_minimum_length",
        canonical_control_ref="CTRL-IAM-002",
        relation="SUPPORTING",
        notes="Password policy supports access control baseline — policy docs still required",
    ),
    CheckControlMapping(
        check_id="cloudtrail_multi_region_enabled",
        canonical_control_ref="CTRL-IR-001",
        relation="SUPPORTING",
        notes="Trail presence supports detection/IR capability — not a full IR runbook",
    ),
]


def resolve_control_refs(
    check_id: str, extra: list[CheckControlMapping] | None = None
) -> list[CheckControlMapping]:
    pool = list(DEFAULT_CHECK_MAPPINGS) + list(extra or [])
    return [m for m in pool if m.check_id == check_id]

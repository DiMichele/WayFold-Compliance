"""Pure state-machine helpers for WayFold Compliance overnight orchestration."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

VALID_STATUSES = {
    "READY",
    "VERIFYING",
    "FIXING",
    "DEVELOPING",
    "AWAITING_VERIFICATION",
    "BLOCKED",
    "HUMAN_REVIEW_REQUIRED",
    "FINAL_REGRESSION",
    "MERGING",
    "COMPLETE",
    "INTERRUPTED",
}

VALID_VERIFICATION = {"PASS", "FAIL", "BLOCKED"}
VALID_DEVELOPMENT = {"IMPLEMENTED", "NOT_STARTED", "BLOCKED", "SKIPPED"}

TRANSITIONS: dict[str, dict[str, Any]] = {
    "1_TO_2": {
        "verify": 1,
        "develop": 2,
        "prompt": "apps/wayfold-compliance/prompts/transition-01-to-02.md",
        "next": "2_TO_3",
    },
    "2_TO_3": {
        "verify": 2,
        "develop": 3,
        "prompt": "apps/wayfold-compliance/prompts/transition-02-to-03.md",
        "next": "3_TO_4",
    },
    "3_TO_4": {
        "verify": 3,
        "develop": 4,
        "prompt": "apps/wayfold-compliance/prompts/transition-03-to-04.md",
        "next": "4_TO_5",
    },
    "4_TO_5": {
        "verify": 4,
        "develop": 5,
        "prompt": "apps/wayfold-compliance/prompts/transition-04-to-05.md",
        "next": "5_TO_6",
    },
    "5_TO_6": {
        "verify": 5,
        "develop": 6,
        "prompt": "apps/wayfold-compliance/prompts/transition-05-to-06.md",
        "next": "CLOSE_6",
    },
    "CLOSE_6": {
        "verify": 6,
        "develop": None,
        "prompt": "apps/wayfold-compliance/prompts/close-phase-06.md",
        "next": None,
        "final_regression": True,
    },
}


def default_state() -> dict[str, Any]:
    return {
        "schemaVersion": 2,
        "project": "wayfold-compliance",
        "lastClosedPhase": 0,
        "implementedPhase": 1,
        "nextTransition": "1_TO_2",
        "status": "READY",
        "verificationAttempts": 0,
        "maxAutomaticFixAttempts": 3,
        "maxPhase": 6,
        "autoCommit": True,
        "autoPush": True,
        "autoTag": True,
        "autoMergeMain": True,
        "blockingIssues": [],
        "branch": "automation/wayfold-compliance",
        "mode": "LOCAL_OVERNIGHT",
        "startedAt": None,
        "updatedAt": None,
        "lastResultPath": None,
        "lastError": None,
        "history": [],
        "notes": (
            "Phase 0 closed via docs/decisions. Automation starts at VERIFY Phase 1 "
            "→ DEVELOP Phase 2. Do not claim Phase 1 COMPLETE until independent PASS."
        ),
    }


def validate_state(state: dict[str, Any]) -> None:
    status = state.get("status")
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    nxt = state.get("nextTransition")
    if nxt is not None and nxt not in TRANSITIONS:
        raise ValueError(f"Unknown nextTransition: {nxt}")
    for key in ("lastClosedPhase", "implementedPhase", "verificationAttempts", "maxPhase"):
        if key in state and not isinstance(state[key], int):
            raise ValueError(f"{key} must be int")


def validate_transition_result(result: dict[str, Any], expected_transition: str) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Result must be a JSON object")
    if result.get("transition") != expected_transition:
        raise ValueError(
            f"Result transition mismatch: got {result.get('transition')!r}, "
            f"expected {expected_transition!r}"
        )
    meta = TRANSITIONS[expected_transition]
    if int(result.get("verifiedPhase", -1)) != int(meta["verify"]):
        raise ValueError("verifiedPhase mismatch")
    vstatus = result.get("verificationStatus")
    if vstatus not in VALID_VERIFICATION:
        raise ValueError(f"Invalid verificationStatus: {vstatus}")
    dstatus = result.get("developmentStatus", "NOT_STARTED")
    if dstatus not in VALID_DEVELOPMENT:
        raise ValueError(f"Invalid developmentStatus: {dstatus}")
    developed = result.get("developedPhase")
    if vstatus == "PASS" and meta["develop"] is not None:
        if developed != meta["develop"] or dstatus != "IMPLEMENTED":
            raise ValueError("PASS requires developedPhase/IMPLEMENTED for this transition")
    if vstatus == "PASS" and meta["develop"] is None:
        if developed is not None:
            raise ValueError("CLOSE_6 PASS must set developedPhase null")
        if dstatus not in {"SKIPPED", "NOT_STARTED"}:
            raise ValueError("CLOSE_6 PASS must use developmentStatus SKIPPED")
    if vstatus != "PASS":
        if developed not in (None, meta["develop"]):
            raise ValueError("On non-PASS, developedPhase must be null or expected next phase")
        if dstatus not in {"NOT_STARTED", "BLOCKED"}:
            raise ValueError("On non-PASS, developmentStatus must be NOT_STARTED or BLOCKED")
    if not isinstance(result.get("blockingIssues", []), list):
        raise ValueError("blockingIssues must be a list")
    return result


def apply_pass_transition(state: dict[str, Any], transition: str) -> dict[str, Any]:
    """Apply successful transition (verify PASS + develop done, or CLOSE_6 verify PASS)."""
    out = deepcopy(state)
    meta = TRANSITIONS[transition]
    closed = int(meta["verify"])
    out["lastClosedPhase"] = closed
    out["verificationAttempts"] = 0
    out["blockingIssues"] = []
    out["lastError"] = None
    if meta.get("final_regression"):
        out["implementedPhase"] = closed
        out["nextTransition"] = None
        out["status"] = "FINAL_REGRESSION"
    else:
        out["implementedPhase"] = int(meta["develop"])
        out["nextTransition"] = meta["next"]
        out["status"] = "READY"
    out.setdefault("history", []).append(
        {"event": "TRANSITION_PASS", "transition": transition, "closedPhase": closed}
    )
    return out


def apply_verification_fail(state: dict[str, Any], issues: list[Any] | None = None) -> dict[str, Any]:
    out = deepcopy(state)
    attempts = int(out.get("verificationAttempts", 0)) + 1
    out["verificationAttempts"] = attempts
    out["blockingIssues"] = issues or out.get("blockingIssues") or []
    max_attempts = int(out.get("maxAutomaticFixAttempts", 3))
    if attempts >= max_attempts:
        out["status"] = "HUMAN_REVIEW_REQUIRED"
        out.setdefault("history", []).append(
            {"event": "HUMAN_REVIEW_REQUIRED", "attempts": attempts}
        )
    else:
        out["status"] = "FIXING"
        out.setdefault("history", []).append({"event": "VERIFY_FAIL", "attempts": attempts})
    return out


def apply_fix_done(state: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(state)
    if out.get("status") == "HUMAN_REVIEW_REQUIRED":
        return out
    out["status"] = "READY"
    out.setdefault("history", []).append({"event": "FIX_DONE"})
    return out


def apply_blocked(state: dict[str, Any], issues: list[Any] | None = None) -> dict[str, Any]:
    out = deepcopy(state)
    out["status"] = "BLOCKED"
    out["blockingIssues"] = issues or []
    out.setdefault("history", []).append({"event": "BLOCKED"})
    return out


def apply_invalid_result(state: dict[str, Any], error: str) -> dict[str, Any]:
    out = deepcopy(state)
    out["status"] = "HUMAN_REVIEW_REQUIRED"
    out["lastError"] = error
    out["blockingIssues"] = [
        {"severity": "BLOCKING", "description": f"Invalid agent output: {error}"}
    ]
    out.setdefault("history", []).append({"event": "INVALID_AGENT_OUTPUT", "error": error})
    return out


def apply_push_failure(state: dict[str, Any], error: str) -> dict[str, Any]:
    out = deepcopy(state)
    out["status"] = "HUMAN_REVIEW_REQUIRED"
    out["lastError"] = error
    out["blockingIssues"] = [{"severity": "BLOCKING", "description": f"Push failure: {error}"}]
    out.setdefault("history", []).append({"event": "PUSH_FAILURE"})
    return out


def apply_merge_conflict(state: dict[str, Any], error: str) -> dict[str, Any]:
    out = deepcopy(state)
    out["status"] = "HUMAN_REVIEW_REQUIRED"
    out["lastError"] = error
    out["blockingIssues"] = [{"severity": "BLOCKING", "description": f"Merge conflict: {error}"}]
    out.setdefault("history", []).append({"event": "MERGE_CONFLICT"})
    return out


def apply_interrupted(state: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(state)
    if out.get("status") not in {"COMPLETE", "HUMAN_REVIEW_REQUIRED"}:
        out["status"] = "INTERRUPTED"
    out.setdefault("history", []).append({"event": "INTERRUPTED"})
    return out


def apply_final_regression_pass(state: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(state)
    out["status"] = "MERGING"
    out.setdefault("history", []).append({"event": "FINAL_REGRESSION_PASS"})
    return out


def apply_final_regression_fail(state: dict[str, Any], attempts: int, max_attempts: int) -> dict[str, Any]:
    out = deepcopy(state)
    out["verificationAttempts"] = attempts
    if attempts >= max_attempts:
        out["status"] = "HUMAN_REVIEW_REQUIRED"
        out.setdefault("history", []).append({"event": "FINAL_REGRESSION_HUMAN_REVIEW"})
    else:
        out["status"] = "FINAL_REGRESSION"
        out.setdefault("history", []).append({"event": "FINAL_REGRESSION_FAIL", "attempts": attempts})
    return out


def apply_complete(state: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(state)
    out["lastClosedPhase"] = 6
    out["implementedPhase"] = 6
    out["nextTransition"] = None
    out["status"] = "COMPLETE"
    out["verificationAttempts"] = 0
    out["blockingIssues"] = []
    out.setdefault("history", []).append({"event": "COMPLETE"})
    return out


def resume_status(state: dict[str, Any]) -> dict[str, Any]:
    """Normalize recoverable statuses for overnight resume."""
    out = deepcopy(state)
    if out.get("status") in {"INTERRUPTED", "FIXING", "VERIFYING", "DEVELOPING", "AWAITING_VERIFICATION"}:
        if out.get("nextTransition") or out.get("status") == "FIXING":
            out["status"] = "READY"
    return out

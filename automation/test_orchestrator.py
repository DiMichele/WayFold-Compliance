#!/usr/bin/env python3
"""Unit tests for WayFold Compliance automation state machine."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state_machine import (
    apply_complete,
    apply_final_regression_fail,
    apply_final_regression_pass,
    apply_fix_done,
    apply_interrupted,
    apply_invalid_result,
    apply_merge_conflict,
    apply_pass_transition,
    apply_push_failure,
    apply_verification_fail,
    default_state,
    resume_status,
    validate_transition_result,
)


class StateMachineTests(unittest.TestCase):
    def test_phase1_pass_to_phase2(self) -> None:
        state = default_state()
        state = apply_pass_transition(state, "1_TO_2")
        self.assertEqual(state["lastClosedPhase"], 1)
        self.assertEqual(state["implementedPhase"], 2)
        self.assertEqual(state["nextTransition"], "2_TO_3")
        self.assertEqual(state["status"], "READY")

    def test_phase2_fail_then_fix(self) -> None:
        state = default_state()
        state["nextTransition"] = "2_TO_3"
        state["lastClosedPhase"] = 1
        state["implementedPhase"] = 2
        state = apply_verification_fail(state, [{"severity": "BLOCKING", "description": "x"}])
        self.assertEqual(state["status"], "FIXING")
        self.assertEqual(state["verificationAttempts"], 1)
        state = apply_fix_done(state)
        self.assertEqual(state["status"], "READY")

    def test_phase2_fail_x3_human_review(self) -> None:
        state = default_state()
        state["maxAutomaticFixAttempts"] = 3
        for _ in range(3):
            state = apply_verification_fail(state, [{"severity": "BLOCKING", "description": "x"}])
        self.assertEqual(state["status"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(state["verificationAttempts"], 3)

    def test_phase3_to_phase4(self) -> None:
        state = default_state()
        state = apply_pass_transition(state, "3_TO_4")
        self.assertEqual(state["lastClosedPhase"], 3)
        self.assertEqual(state["implementedPhase"], 4)
        self.assertEqual(state["nextTransition"], "4_TO_5")

    def test_phase6_to_final_regression(self) -> None:
        state = default_state()
        state = apply_pass_transition(state, "CLOSE_6")
        self.assertEqual(state["lastClosedPhase"], 6)
        self.assertEqual(state["implementedPhase"], 6)
        self.assertIsNone(state["nextTransition"])
        self.assertEqual(state["status"], "FINAL_REGRESSION")

    def test_final_pass_merge_complete(self) -> None:
        state = default_state()
        state = apply_pass_transition(state, "CLOSE_6")
        state = apply_final_regression_pass(state)
        self.assertEqual(state["status"], "MERGING")
        state = apply_complete(state)
        self.assertEqual(state["status"], "COMPLETE")
        self.assertEqual(state["lastClosedPhase"], 6)
        self.assertIsNone(state["nextTransition"])

    def test_invalid_json_safe_stop(self) -> None:
        state = apply_invalid_result(default_state(), "broken")
        self.assertEqual(state["status"], "HUMAN_REVIEW_REQUIRED")

    def test_push_failure_safe_stop(self) -> None:
        state = apply_push_failure(default_state(), "auth")
        self.assertEqual(state["status"], "HUMAN_REVIEW_REQUIRED")

    def test_merge_conflict_safe_stop(self) -> None:
        state = apply_merge_conflict(default_state(), "conflict")
        self.assertEqual(state["status"], "HUMAN_REVIEW_REQUIRED")

    def test_interruption_recoverable(self) -> None:
        state = default_state()
        state["status"] = "VERIFYING"
        state = apply_interrupted(state)
        self.assertEqual(state["status"], "INTERRUPTED")
        state = resume_status(state)
        self.assertEqual(state["status"], "READY")

    def test_final_regression_fail_no_complete(self) -> None:
        state = apply_pass_transition(default_state(), "CLOSE_6")
        state = apply_final_regression_fail(state, 3, 3)
        self.assertEqual(state["status"], "HUMAN_REVIEW_REQUIRED")
        self.assertNotEqual(state["status"], "COMPLETE")

    def test_validate_result_pass(self) -> None:
        result = {
            "transition": "1_TO_2",
            "verifiedPhase": 1,
            "verificationStatus": "PASS",
            "developedPhase": 2,
            "developmentStatus": "IMPLEMENTED",
            "blockingIssues": [],
        }
        validate_transition_result(result, "1_TO_2")

    def test_validate_result_reject_wrong_transition(self) -> None:
        with self.assertRaises(ValueError):
            validate_transition_result(
                {
                    "transition": "2_TO_3",
                    "verifiedPhase": 1,
                    "verificationStatus": "PASS",
                    "developedPhase": 2,
                    "developmentStatus": "IMPLEMENTED",
                    "blockingIssues": [],
                },
                "1_TO_2",
            )

    def test_atomic_write(self) -> None:
        from wayfold_orchestrator import atomic_write_json

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            atomic_write_json(path, {"ok": True})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["ok"], True)


if __name__ == "__main__":
    raise SystemExit(unittest.main())

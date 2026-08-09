from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api import Handler
from engine.authz import assert_tenant_access
from engine.checklist import build_unified_checklist
from engine.cli import main as cli_main
from engine.domain import (
    CoverageRelation,
    ImplementationStatus,
    RequirementCoverage,
)
from engine.impact import rank_control_impact
from engine.program_loader import load_program_snapshot
from engine.readiness import framework_readiness, _requirement_coverage


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "michele_phase2_program.json"


class UnifiedComplianceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.program = load_program_snapshot(FIXTURE)
        cls.checklist = build_unified_checklist(cls.program)

    def test_dedup_three_frameworks_to_one_control(self):
        iam = [c for c in self.checklist.controls if c.canonical_control_ref == "CTRL-IAM-001"]
        self.assertEqual(len(iam), 1)
        fws = {c.framework_id for c in iam[0].framework_coverage}
        self.assertEqual(fws, {"fw-a", "fw-b", "fw-c"})

    def test_partial_remains_partial(self):
        iam = next(c for c in self.checklist.controls if c.canonical_control_ref == "CTRL-IAM-001")
        partials = [c for c in iam.framework_coverage if c.relation == CoverageRelation.PARTIAL]
        self.assertGreaterEqual(len(partials), 1)
        self.assertTrue(any(c.uncovered_delta for c in partials))
        # Implemented + PARTIAL must not be treated as FULL in readiness
        ready = framework_readiness(self.program, self.checklist)
        fw_a = next(r for r in ready if r.framework_id == "fw-a")
        self.assertEqual(
            fw_a.requirement_breakdown["req-a-02"],
            RequirementCoverage.PARTIALLY_COVERED,
        )

    def test_unmapped_remain_visible(self):
        codes = {u.code for u in self.checklist.unmapped}
        self.assertIn("A.9.9", codes)
        self.assertIn("NIS2-X9", codes)
        self.assertGreaterEqual(len(self.checklist.unmapped), 2)

    def test_version_pinning_preserved(self):
        for cov in self.checklist.controls[0].framework_coverage:
            self.assertTrue(cov.framework_version)
        for u in self.checklist.unmapped:
            self.assertTrue(u.framework_version)

    def test_supporting_relation(self):
        iam = next(c for c in self.checklist.controls if c.canonical_control_ref == "CTRL-IAM-001")
        supporting = [c for c in iam.framework_coverage if c.relation == CoverageRelation.SUPPORTING]
        self.assertEqual(len(supporting), 1)
        self.assertIn("recovery", supporting[0].uncovered_delta.lower())

    def test_mixed_implementation_statuses(self):
        statuses = {c.status for c in self.checklist.controls}
        self.assertIn(ImplementationStatus.IMPLEMENTED, statuses)
        self.assertIn(ImplementationStatus.IN_PROGRESS, statuses)
        self.assertIn(ImplementationStatus.NOT_IMPLEMENTED, statuses)

    def test_control_impact_readable(self):
        impact = rank_control_impact(self.program, self.checklist)
        self.assertTrue(impact)
        top = impact[0]
        self.assertIn("requisiti", top.readable_summary)
        self.assertIn("framework", top.readable_summary)
        # Open IR control should rank high
        refs = [r.canonical_control_ref for r in impact]
        self.assertIn("CTRL-IR-001", refs)

    def test_tenant_isolation_gate(self):
        denied = assert_tenant_access(
            actor_tenant_ids={"tenant-other"},
            is_superuser=False,
            target_tenant_id="tenant-michele",
        )
        self.assertFalse(denied.allowed)
        allowed = assert_tenant_access(
            actor_tenant_ids={"tenant-michele"},
            is_superuser=False,
            target_tenant_id="tenant-michele",
        )
        self.assertTrue(allowed.allowed)

    def test_counts(self):
        self.assertEqual(self.checklist.raw_requirement_count, 8)
        self.assertEqual(self.checklist.unified_control_count, 3)

    def test_not_applicable_coverage(self):
        cov = _requirement_coverage(
            CoverageRelation.FULL,
            ImplementationStatus.IMPLEMENTED,
            "not_applicable",
        )
        self.assertEqual(cov, RequirementCoverage.NOT_APPLICABLE)
        program = replace(
            self.program,
            requirements=[
                replace(self.program.requirements[0], result="not_applicable"),
                *self.program.requirements[1:],
            ],
        )
        checklist = build_unified_checklist(program)
        ready = framework_readiness(program, checklist)
        fw_a = next(r for r in ready if r.framework_id == "fw-a")
        self.assertEqual(
            fw_a.requirement_breakdown["req-a-01"],
            RequirementCoverage.NOT_APPLICABLE,
        )
        self.assertGreaterEqual(fw_a.not_applicable, 1)

    def test_cli_default_deny_without_auth(self):
        code = cli_main(["--format", "json"])
        self.assertEqual(code, 2)

    def test_cli_cross_tenant_denied(self):
        code = cli_main(["--actor-tenants", "tenant-other", "--format", "json"])
        self.assertEqual(code, 2)

    def test_api_auth_default_deny_and_rbac(self):
        captured: dict = {}

        class FakeHandler(Handler):
            def __init__(self, path: str):
                self.path = path
                self.wfile = mock.Mock()
                self.wfile.write = lambda b: captured.setdefault("body", b)
                captured.clear()
                captured["status"] = None
                captured["headers"] = {}

            def send_response(self, code, message=None):  # noqa: ARG002
                captured["status"] = code

            def send_header(self, key, value):
                captured["headers"][key] = value

            def end_headers(self):
                return None

            def address_string(self):
                return "test"

        # No credentials → 401
        FakeHandler(f"/api/unified-checklist?program={FIXTURE.as_posix()}").do_GET()
        self.assertEqual(captured["status"], 401)
        self.assertIn("authentication_required", captured["body"].decode())

        # Wrong tenant → 403
        FakeHandler(
            f"/api/unified-checklist?program={FIXTURE.as_posix()}"
            "&actor_tenants=tenant-other"
        ).do_GET()
        self.assertEqual(captured["status"], 403)

        # Correct tenant → 200 with checklist service payload
        FakeHandler(
            f"/api/unified-checklist?program={FIXTURE.as_posix()}"
            "&actor_tenants=tenant-michele"
        ).do_GET()
        self.assertEqual(captured["status"], 200)
        payload = json.loads(captured["body"].decode())
        self.assertIn("checklist", payload)
        self.assertIn("readiness", payload)
        self.assertIn("impact", payload)
        self.assertGreaterEqual(len(payload["checklist"]["unmapped"]), 2)


if __name__ == "__main__":
    unittest.main()

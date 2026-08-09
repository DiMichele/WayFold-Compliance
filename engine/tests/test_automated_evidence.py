from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api import Handler
from engine.automated_evidence import pages as auto_ev_pages
from engine.automated_evidence.adapters import ProwlerJsonAdapter
from engine.automated_evidence.demo import run_demo_ingest, seed_demo_connector
from engine.automated_evidence.domain import (
    ConnectorConfig,
    ConnectorKind,
    EvidenceReviewStatus,
    FindingStatus,
)
from engine.automated_evidence.service import AutomatedEvidenceService
from engine.automated_evidence.store import AutomatedEvidenceStore
from engine.program_loader import load_program_snapshot
from engine.ui_shell import WAYFOLD_CSS

FIXTURES = ROOT / "engine" / "fixtures"
PROWLER_FIXTURE = FIXTURES / "automated_evidence" / "prowler-aws-sample.json"


class AutomatedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AutomatedEvidenceStore(Path(self.tmp.name) / "auto_ev")
        self.svc = AutomatedEvidenceService(self.store)
        self.program = load_program_snapshot(FIXTURES / "michele_phase2_program.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_prowler_adapter_normalizes_findings(self):
        findings = ProwlerJsonAdapter().parse(
            PROWLER_FIXTURE, observed_at="2026-08-09T00:00:00+00:00"
        )
        self.assertGreaterEqual(len(findings), 3)
        ids = {f.check_id for f in findings}
        self.assertIn("iam_root_mfa_enabled", ids)
        root = next(f for f in findings if f.check_id == "iam_root_mfa_enabled")
        self.assertEqual(root.status, FindingStatus.PASS)
        self.assertTrue(root.content_hash)

    def test_ingest_maps_to_controls_idempotent(self):
        seed_demo_connector(self.store, tenant_id=self.program.tenant_id)
        first = self.svc.ingest_connector(
            "conn-prowler-michele-demo",
            program=self.program,
            is_superuser=True,
        )
        self.assertIn(first.status.value, {"OK", "PARTIAL"})
        self.assertGreaterEqual(first.created, 1)
        self.assertGreaterEqual(first.unmapped, 1)  # unmapped_example_s3_public
        second = self.svc.ingest_connector(
            "conn-prowler-michele-demo",
            program=self.program,
            is_superuser=True,
        )
        self.assertEqual(second.created, 0)
        self.assertGreaterEqual(second.skipped_duplicate, 1)
        records = self.svc.list_evidence(is_superuser=True)
        refs = {r.canonical_control_ref for r in records}
        self.assertIn("CTRL-IAM-001", refs)
        self.assertIn("CTRL-IAM-002", refs)
        self.assertTrue(all(r.review_status == EvidenceReviewStatus.PENDING_REVIEW for r in records))
        self.assertTrue(all(r.requires_manual_review for r in records))

    def test_pass_does_not_auto_set_compliance(self):
        seed_demo_connector(self.store)
        before = {
            i.ref_id: i.status.value for i in self.program.implementations
        }
        self.svc.ingest_connector(
            "conn-prowler-michele-demo",
            program=self.program,
            is_superuser=True,
        )
        after = {
            i.ref_id: i.status.value for i in self.program.implementations
        }
        self.assertEqual(before, after)
        # Even after approve, projection is advisory counts only
        for r in self.svc.list_evidence(is_superuser=True):
            if r.finding_status == FindingStatus.PASS:
                self.svc.review_evidence(
                    r.id, status=EvidenceReviewStatus.APPROVED, is_superuser=True
                )
        counts = self.svc.project_evidence_counts(self.program)
        self.assertTrue(counts)
        after_approve = {
            i.ref_id: i.status.value for i in self.program.implementations
        }
        self.assertEqual(before, after_approve)

    def test_tenant_isolation(self):
        seed_demo_connector(self.store, tenant_id="tenant-michele")
        self.svc.ingest_connector(
            "conn-prowler-michele-demo", program=self.program, is_superuser=True
        )
        limited = self.svc.list_evidence(
            actor_tenant_ids={"tenant-alfa"}, is_superuser=False
        )
        self.assertEqual(limited, [])
        with self.assertRaises(PermissionError):
            self.svc.ingest_connector(
                "conn-prowler-michele-demo",
                actor_tenant_ids={"tenant-alfa"},
                is_superuser=False,
            )
        rec = self.svc.list_evidence(is_superuser=True)[0]
        with self.assertRaises(PermissionError):
            self.svc.review_evidence(
                rec.id,
                status=EvidenceReviewStatus.APPROVED,
                actor_tenant_ids={"tenant-alfa"},
                is_superuser=False,
            )

    def test_scanner_failure_isolated(self):
        bad = ConnectorConfig(
            id="conn-broken",
            tenant_id="tenant-michele",
            name="Broken",
            kind=ConnectorKind.PROWLER_JSON,
            source_uri="fixture://does-not-exist.json",
        )
        self.svc.upsert_connector(bad)
        before = len(self.svc.list_evidence(is_superuser=True))
        result = self.svc.ingest_connector("conn-broken", is_superuser=True)
        self.assertEqual(result.status.value, "FAILED")
        self.assertTrue(result.errors)
        self.assertEqual(len(self.svc.list_evidence(is_superuser=True)), before)

    def test_no_inline_secrets_in_store(self):
        conn = ConnectorConfig(
            id="conn-safe",
            tenant_id="tenant-michele",
            name="Safe",
            kind=ConnectorKind.PROWLER_JSON,
            source_uri=f"fixture://prowler-aws-sample.json",
            credential_ref="PROWLER_AWS_ROLE_ARN",
        )
        self.svc.upsert_connector(conn)
        raw = (self.store.root / "connectors.json").read_text(encoding="utf-8")
        self.assertNotIn("AKIA", raw)
        data = json.loads(raw)
        row = next(c for c in data["connectors"] if c["id"] == "conn-safe")
        self.assertEqual(row.get("credential_ref"), "PROWLER_AWS_ROLE_ARN")
        self.assertNotIn("credential", row)
        self.assertNotIn("api_key", row)
        self.assertNotIn("password", row)
        self.assertNotIn("secret", row)

    def test_stale_on_changed_finding(self):
        seed_demo_connector(self.store)
        self.svc.ingest_connector(
            "conn-prowler-michele-demo", program=self.program, is_superuser=True
        )
        # Mutate fixture content for same check/resource
        mutated = json.loads(PROWLER_FIXTURE.read_text(encoding="utf-8"))
        mutated[0]["StatusExtended"] = "MFA still enabled — rechecked detail changed"
        result = self.svc.ingest_connector(
            "conn-prowler-michele-demo",
            program=self.program,
            is_superuser=True,
            payload=json.dumps(mutated),
        )
        self.assertGreaterEqual(result.updated, 1)
        statuses = {
            r.review_status
            for r in self.svc.list_evidence(is_superuser=True)
            if r.check_id == "iam_root_mfa_enabled"
        }
        self.assertIn(EvidenceReviewStatus.STALE, statuses)
        self.assertIn(EvidenceReviewStatus.PENDING_REVIEW, statuses)

    def test_api_requires_auth(self):
        import engine.api as api_mod

        original = api_mod._auto_ev_service
        api_mod._auto_ev_service = lambda: self.svc
        try:
            captured: dict = {}

            class FakeHandler(Handler):
                def __init__(self, path: str):
                    self.path = path
                    self.wfile = mock.Mock()
                    self.wfile.write = lambda b: captured.__setitem__("body", b)
                    captured["status"] = None

                def send_response(self, code, message=None):  # noqa: ARG002
                    captured["status"] = code

                def send_header(self, key, value):
                    return None

                def end_headers(self):
                    return None

                def address_string(self):
                    return "test"

            FakeHandler("/api/auto-evidence").do_GET()
            self.assertEqual(captured["status"], 401)
        finally:
            api_mod._auto_ev_service = original

    def test_demo_cycle(self):
        out = run_demo_ingest(self.store, program=self.program)
        self.assertGreaterEqual(out["first"].created, 1)
        self.assertGreaterEqual(out["second"].skipped_duplicate, 1)

    def test_pages_use_wayfold_ui_shell(self):
        html = auto_ev_pages.connectors_page([], "superuser=1")
        self.assertIn("WayFold", html)
        self.assertIn("--wf-primary:#675cf2", html)
        self.assertIn("Inter", html)
        self.assertIn("sidebar", html)
        self.assertIn(WAYFOLD_CSS[:40], html)
        self.assertNotIn("#f6f7f9", html)
        self.assertNotIn("--acc:#d97b5c", html)
        ev_html = auto_ev_pages.evidence_page([], "superuser=1")
        self.assertIn("WayFold", ev_html)
        self.assertIn("--wf-primary:#675cf2", ev_html)


if __name__ == "__main__":
    unittest.main()

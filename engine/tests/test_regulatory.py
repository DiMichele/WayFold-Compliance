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
from engine.regulatory.demo import run_demo_change_cycle, seed_demo_source
from engine.regulatory.diff import classify_relevance
from engine.regulatory.domain import ChangeStatus, SourceType
from engine.regulatory.fetch import validate_url
from engine.regulatory.normalize import normalize_html
from engine.regulatory.pipeline import check_source, impact_for_change, review_change
from engine.regulatory.store import RegulatoryStore

FIXTURE_ROOT = ROOT / "engine" / "fixtures" / "regulatory"


class RegulatoryIntelligenceTests(unittest.TestCase):
    def setUp(self):
        import os

        os.environ["WAYFOLD_TEST_MODE"] = "1"
        self.tmp = tempfile.TemporaryDirectory()
        self.store = RegulatoryStore(Path(self.tmp.name))

    def tearDown(self):
        import os

        os.environ.pop("WAYFOLD_TEST_MODE", None)
        self.tmp.cleanup()

    def test_normalize_strips_script_style(self):
        html = "<html><script>x()</script><style>.a{}</style><p>Hello</p></html>"
        self.assertEqual(normalize_html(html), "Hello")

    def test_cosmetic_vs_substantive(self):
        self.assertEqual(
            classify_relevance(raw_changed=True, normalized_changed=False),
            "COSMETIC",
        )
        self.assertEqual(
            classify_relevance(raw_changed=True, normalized_changed=True),
            "SUBSTANTIVE",
        )

    def test_url_validation_blocks_private_schemes(self):
        self.assertIsNone(validate_url("fixture://demo-nis2/v1.html"))
        self.assertEqual(validate_url("ftp://example.com/x"), "unsupported_scheme:ftp")

    def test_demo_cycle_creates_change_and_impact(self):
        cycle = run_demo_change_cycle(self.store, fixture_root=FIXTURE_ROOT)
        self.assertTrue(cycle["baseline"].ok)
        self.assertFalse(cycle["baseline"].changed)
        self.assertTrue(cycle["changed"].ok)
        self.assertTrue(cycle["changed"].changed)
        self.assertIsNotNone(cycle["changed"].change_id)

        change = self.store.get_change(cycle["changed"].change_id)
        assert change is not None
        self.assertEqual(change.status, ChangeStatus.NEW)
        self.assertEqual(change.relevance, "SUBSTANTIVE")
        self.assertIn("sei mesi", change.raw_diff.lower() + change.summary.lower())

        # Superuser sees full advisory impact
        impact = impact_for_change(change.id, self.store, is_superuser=True)
        self.assertGreaterEqual(impact.clients, 1)
        self.assertGreaterEqual(impact.controls, 1)
        self.assertTrue(any(r.tenant_id == "tenant-michele" for r in impact.rows))

        reviewed = review_change(change.id, self.store, status=ChangeStatus.ACCEPTED)
        self.assertEqual(reviewed.status, ChangeStatus.ACCEPTED)
        suggestions = self.store.list_suggestions()
        self.assertTrue(suggestions)
        self.assertEqual(suggestions[0].suggested_action, "CLONE_DRAFT")
        # Still no mutation of CISO — suggestion is engine-only
        self.assertEqual(suggestions[0].status.value, "READY_FOR_HUMAN")

    def test_impact_tenant_isolation(self):
        """Actor limited to Michele must not see Alfa rows on a multi-tenant hit."""
        source = self.store.create_source(
            title="Shared frameworks notice",
            url="fixture://demo-nis2/v1.html",
            type=SourceType.HTML,
            linked_framework_ids=["fw-b", "fw-nis2"],
            linked_framework_versions=["2026.1"],
            linked_requirement_ids=["req-b-01", "NIS2-IAM", "alfa-req-03", "NIS2-LOG"],
        )
        check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        source.url = "fixture://demo-nis2/v2.html"
        self.store.upsert_source(source)
        result = check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        self.assertTrue(result.changed)
        assert result.change_id

        full = impact_for_change(result.change_id, self.store, is_superuser=True)
        tenants_full = {r.tenant_id for r in full.rows}
        self.assertIn("tenant-michele", tenants_full)
        self.assertIn("tenant-alfa", tenants_full)

        limited = impact_for_change(
            result.change_id,
            self.store,
            actor_tenant_ids={"tenant-michele"},
            is_superuser=False,
        )
        tenants_limited = {r.tenant_id for r in limited.rows}
        self.assertEqual(tenants_limited, {"tenant-michele"})
        self.assertNotIn("tenant-alfa", tenants_limited)

        empty = impact_for_change(
            result.change_id,
            self.store,
            actor_tenant_ids=set(),
            is_superuser=False,
        )
        self.assertEqual(empty.rows, [])

    def test_snapshots_append_only_with_stable_hashes(self):
        from engine.regulatory.hashutil import content_hash
        from engine.regulatory.normalize import normalize_html

        source = seed_demo_source(self.store, url="fixture://demo-nis2/v1.html")
        check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        snaps1 = self.store.list_snapshots(source.id)
        self.assertEqual(len(snaps1), 1)
        first = snaps1[0]
        raw = self.store.read_blob(first.raw_ref)
        self.assertEqual(first.content_hash, content_hash(raw))
        self.assertEqual(first.normalized_hash, content_hash(normalize_html(raw)))

        source.url = "fixture://demo-nis2/v2.html"
        self.store.upsert_source(source)
        check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        snaps2 = self.store.list_snapshots(source.id)
        self.assertEqual(len(snaps2), 2)
        # Previous snapshot record unchanged
        still = self.store.get_snapshot(first.id)
        assert still is not None
        self.assertEqual(still.content_hash, first.content_hash)
        self.assertEqual(still.normalized_hash, first.normalized_hash)
        self.assertEqual(still.raw_ref, first.raw_ref)

    def test_cosmetic_html_does_not_create_change(self):
        source = seed_demo_source(self.store, url="fixture://demo-nis2/v1.html")
        check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        source.url = "fixture://demo-nis2/v1-cosmetic.html"
        self.store.upsert_source(source)
        result = check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        self.assertTrue(result.ok)
        self.assertFalse(result.changed)
        self.assertEqual(result.relevance, "COSMETIC")
        self.assertEqual(self.store.list_changes(), [])

    def test_failed_source_does_not_block_others(self):
        bad = self.store.create_source(
            title="Broken",
            url="fixture://missing/nope.html",
            type=SourceType.HTML,
            monitoring_enabled=True,
        )
        good = seed_demo_source(self.store)
        from engine.regulatory.pipeline import run_monitoring_pass

        results = run_monitoring_pass(self.store, fixture_root=FIXTURE_ROOT)
        by_id = {r.source_id: r for r in results}
        self.assertFalse(by_id[bad.id].ok)
        self.assertTrue(by_id[good.id].ok)

    def test_api_sources_require_auth(self):
        captured: dict = {}

        class FakeHandler(Handler):
            def __init__(self, path: str):
                self.path = path
                self.wfile = mock.Mock()
                self.wfile.write = lambda b: captured.__setitem__("body", b)
                captured.clear()
                captured["status"] = None

            def send_response(self, code, message=None):  # noqa: ARG002
                captured["status"] = code

            def send_header(self, key, value):
                return None

            def end_headers(self):
                return None

            def address_string(self):
                return "test"

        FakeHandler("/api/sources").do_GET()
        self.assertEqual(captured["status"], 401)

        FakeHandler("/api/sources?superuser=1").do_GET()
        self.assertEqual(captured["status"], 200)
        payload = json.loads(captured["body"].decode())
        self.assertIn("sources", payload)

    def test_api_impact_filters_by_actor_tenant(self):
        source = self.store.create_source(
            title="Shared frameworks notice",
            url="fixture://demo-nis2/v1.html",
            type=SourceType.HTML,
            linked_framework_ids=["fw-b", "fw-nis2"],
            linked_framework_versions=["2026.1"],
            linked_requirement_ids=["req-b-01", "NIS2-IAM", "alfa-req-03", "NIS2-LOG"],
        )
        check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        source.url = "fixture://demo-nis2/v2.html"
        self.store.upsert_source(source)
        result = check_source(source, self.store, fixture_root=FIXTURE_ROOT)
        assert result.change_id

        import engine.api as api_mod

        original = api_mod._reg_store
        api_mod._reg_store = lambda: self.store
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

            FakeHandler(
                f"/api/regulatory/impact?change_id={result.change_id}"
                "&actor_tenants=tenant-michele"
            ).do_GET()
            self.assertEqual(captured["status"], 200)
            payload = json.loads(captured["body"].decode())
            tenants = {r["tenant_id"] for r in payload["impact"]["rows"]}
            self.assertEqual(tenants, {"tenant-michele"})
        finally:
            api_mod._reg_store = original


if __name__ == "__main__":
    unittest.main()

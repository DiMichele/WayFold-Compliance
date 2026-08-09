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
from engine.ai.domain import SuggestionReviewStatus
from engine.ai.provider import HeuristicAIProvider
from engine.ai.service import AIAssistanceService, AIProcessingDisabled
from engine.ai.store import AIStore
from engine.program_loader import load_program_snapshot
from engine.regulatory.demo import run_demo_change_cycle
from engine.regulatory.store import RegulatoryStore

FIXTURES = ROOT / "engine" / "fixtures"
REG_FIXTURES = FIXTURES / "regulatory"


class AIAssistanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.ai_store = AIStore(root / "ai")
        self.reg_store = RegulatoryStore(root / "reg")
        self.svc = AIAssistanceService(
            store=self.ai_store,
            provider=HeuristicAIProvider(),
            regulatory_store=self.reg_store,
        )
        self.program = load_program_snapshot(FIXTURES / "michele_phase2_program.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ai_disabled_by_default(self):
        settings = self.svc.tenant_settings(self.program.tenant_id)
        self.assertFalse(settings.ai_processing_enabled)
        with self.assertRaises(AIProcessingDisabled):
            self.svc.suggest_mapping(self.program, "req-a-99")

    def test_mapping_suggestion_requires_human_review(self):
        self.svc.set_ai_processing(self.program.tenant_id, True)
        sug = self.svc.suggest_mapping(self.program, "req-a-99")
        self.assertEqual(sug.review_status, SuggestionReviewStatus.AI_SUGGESTED)
        self.assertEqual(sug.kind.value, "MAPPING")
        # Cannot materialize before approve
        with self.assertRaises(ValueError):
            self.svc.materialize_approved_mapping(sug.id, self.program)
        approved = self.svc.review_suggestion(
            sug.id,
            status=SuggestionReviewStatus.APPROVED,
            is_superuser=True,
        )
        self.assertEqual(approved.review_status, SuggestionReviewStatus.APPROVED)
        if sug.payload.get("suggested_control_ref"):
            mapping = self.svc.materialize_approved_mapping(sug.id, self.program)
            self.assertEqual(mapping.review_status.value, "APPROVED")
            self.assertIn("human-approved", mapping.notes.lower())

    def test_reject_blocks_materialize(self):
        self.svc.set_ai_processing(self.program.tenant_id, True)
        sug = self.svc.suggest_mapping(self.program, "req-b-01")
        self.svc.review_suggestion(
            sug.id, status=SuggestionReviewStatus.REJECTED, is_superuser=True
        )
        with self.assertRaises(ValueError):
            self.svc.materialize_approved_mapping(sug.id, self.program)

    def test_gap_explanation(self):
        self.svc.set_ai_processing(self.program.tenant_id, True)
        sug = self.svc.explain_gap(self.program, "req-a-99")
        self.assertEqual(sug.kind.value, "GAP_EXPLANATION")
        self.assertEqual(sug.review_status, SuggestionReviewStatus.AI_SUGGESTED)
        self.assertIn("missing_elements", sug.payload)
        self.assertFalse(sug.payload.get("closes_gap", False))

    def test_regulatory_and_impact_suggestions(self):
        self.svc.set_ai_processing(self.program.tenant_id, True)
        cycle = run_demo_change_cycle(self.reg_store, fixture_root=REG_FIXTURES)
        change_id = cycle["changed"].change_id
        assert change_id
        reg = self.svc.summarize_regulatory_change(
            change_id, tenant_id=self.program.tenant_id, program=self.program
        )
        self.assertEqual(reg.kind.value, "REGULATORY_DIFF")
        self.assertTrue(reg.payload.get("is_relevant"))
        impact = self.svc.suggest_impact(
            change_id,
            tenant_id=self.program.tenant_id,
            actor_tenant_ids={self.program.tenant_id},
            is_superuser=False,
        )
        self.assertEqual(impact.kind.value, "IMPACT")
        self.assertIn("advisory", impact.payload.get("narrative", "").lower())

    def test_suggestion_list_tenant_isolation(self):
        self.svc.set_ai_processing("tenant-michele", True)
        self.svc.set_ai_processing("tenant-alfa", True)
        self.svc.suggest_mapping(self.program, "req-a-01")
        alfa = load_program_snapshot(FIXTURES / "alfa_phase3_program.json")
        self.svc.suggest_mapping(alfa, "alfa-req-99")
        limited = self.svc.list_suggestions(
            actor_tenant_ids={"tenant-michele"}, is_superuser=False
        )
        self.assertTrue(limited)
        self.assertTrue(all(s.tenant_id == "tenant-michele" for s in limited))

    def test_api_requires_auth_and_respects_disabled(self):
        import engine.api as api_mod

        original = api_mod._ai_service
        api_mod._ai_service = lambda: self.svc
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

            FakeHandler("/api/ai/suggestions").do_GET()
            self.assertEqual(captured["status"], 401)

            FakeHandler(
                "/api/ai/mapping-suggest?superuser=1&requirement_id=req-a-99"
            ).do_GET()
            self.assertEqual(captured["status"], 403)
            body = json.loads(captured["body"].decode())
            self.assertIn("ai_processing_disabled", body["error"])
        finally:
            api_mod._ai_service = original

    def test_no_auto_approve_on_suggest(self):
        self.svc.set_ai_processing(self.program.tenant_id, True)
        for fn in (
            lambda: self.svc.suggest_mapping(self.program, "req-b-02"),
            lambda: self.svc.explain_gap(self.program, "req-b-02"),
        ):
            sug = fn()
            self.assertEqual(sug.review_status, SuggestionReviewStatus.AI_SUGGESTED)

    def test_cross_tenant_review_denied(self):
        self.svc.set_ai_processing(self.program.tenant_id, True)
        sug = self.svc.suggest_mapping(self.program, "req-a-99")
        with self.assertRaises(PermissionError):
            self.svc.review_suggestion(
                sug.id,
                status=SuggestionReviewStatus.APPROVED,
                actor_tenant_ids={"tenant-alfa"},
                is_superuser=False,
            )

    def test_regulatory_summary_drops_mismatched_program_context(self):
        """Alfa tenant must not receive Michele requirement IDs via default program."""
        import engine.api as api_mod

        self.svc.set_ai_processing("tenant-alfa", True)
        cycle = run_demo_change_cycle(self.reg_store, fixture_root=REG_FIXTURES)
        change_id = cycle["changed"].change_id
        assert change_id
        michele_req_ids = {r.id for r in self.program.requirements}

        original = api_mod._ai_service
        api_mod._ai_service = lambda: self.svc
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

            # No program_id: must not inject default Michele program reqs into Alfa AI payload.
            # Global source-linked IDs (e.g. req-b-01) may still appear — that is KB-level, not a leak.
            FakeHandler(
                f"/api/ai/regulatory-summary?actor_tenants=tenant-alfa"
                f"&tenant_id=tenant-alfa&change_id={change_id}"
            ).do_GET()
            self.assertEqual(captured["status"], 200)
            body = json.loads(captured["body"].decode())
            impacted = set(body["payload"].get("potentially_impacted_requirement_ids") or [])
            program_only = michele_req_ids - {"req-b-01"}  # req-b-01 is also source-linked globally
            self.assertFalse(impacted & program_only)
            self.assertNotIn("req-a-99", impacted)
        finally:
            api_mod._ai_service = original


if __name__ == "__main__":
    unittest.main()

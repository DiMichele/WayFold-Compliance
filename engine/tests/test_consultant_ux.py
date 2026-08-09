from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api import Handler
from engine.consultant_views import (
    control_detail,
    deadline_view,
    evidence_view,
    owner_view,
    task_view,
)
from engine.gap_assessment import GapFilter, build_gap_rows, filter_gap_rows
from engine.portfolio import build_client_dashboard, build_portfolio
from engine.program_loader import load_program_snapshot
from engine.reports import report_csv, report_html
from engine import ux_pages

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MICHELE = FIXTURES / "michele_phase2_program.json"
ALFA = FIXTURES / "alfa_phase3_program.json"
AS_OF = date(2026, 8, 9)


class ConsultantUxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.michele = load_program_snapshot(MICHELE)
        cls.alfa = load_program_snapshot(ALFA)

    def test_portfolio_hides_unauthorized_tenant(self):
        rows = build_portfolio(
            actor_tenant_ids={"tenant-michele"},
            is_superuser=False,
            as_of=AS_OF,
        )
        tenants = {r.tenant_id for r in rows}
        self.assertEqual(tenants, {"tenant-michele"})
        self.assertNotIn("tenant-alfa", tenants)

    def test_portfolio_superuser_sees_all(self):
        rows = build_portfolio(
            actor_tenant_ids=set(),
            is_superuser=True,
            as_of=AS_OF,
        )
        tenants = {r.tenant_id for r in rows}
        self.assertEqual(tenants, {"tenant-michele", "tenant-alfa"})

    def test_client_dashboard_counts(self):
        dash = build_client_dashboard(self.michele, as_of=AS_OF)
        self.assertEqual(dash.tenant_id, "tenant-michele")
        self.assertEqual(dash.raw_requirements, 8)
        self.assertEqual(dash.unified_controls, 3)
        self.assertEqual(dash.unmapped_count, 2)
        self.assertGreaterEqual(dash.missing_evidence, 1)
        self.assertTrue(dash.readiness)
        self.assertTrue(dash.frameworks)

    def test_gap_filters_coherent(self):
        rows = build_gap_rows(self.michele)
        self.assertGreaterEqual(len(rows), 6)
        unmapped = filter_gap_rows(rows, GapFilter(mapped=False))
        self.assertTrue(all(not r.mapped for r in unmapped))
        self.assertGreaterEqual(len(unmapped), 2)
        partial = filter_gap_rows(rows, GapFilter(search="PARTIAL"))
        self.assertTrue(partial)
        self.assertTrue(all("PARTIAL" in (r.mapping or "").upper() or "partial" in (r.gap or "").lower() for r in partial))
        by_fw = filter_gap_rows(rows, GapFilter(framework="NIS2"))
        self.assertTrue(all("NIS2" in r.framework_name for r in by_fw))
        missing = filter_gap_rows(rows, GapFilter(missing_evidence=True))
        self.assertTrue(all(r.mapped and r.evidence_count <= 0 for r in missing))
        self.assertGreaterEqual(len(missing), 1)
        by_deadline = filter_gap_rows(
            rows, GapFilter(deadline_after="2026-09-01", deadline_before="2026-09-30")
        )
        self.assertTrue(by_deadline)
        self.assertTrue(all(r.deadline and "2026-09" in r.deadline for r in by_deadline))

    def test_control_detail_from_gap_drilldown(self):
        detail = control_detail(self.michele, "CTRL-IAM-001")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertGreaterEqual(len(detail.framework_coverage), 2)
        self.assertTrue(any(c.uncovered_delta for c in detail.framework_coverage))
        self.assertEqual(detail.evidence_count, 1)
        self.assertEqual(detail.open_task_count, 0)
        html = ux_pages.control_page(
            detail, "superuser=1&program_id=program-cyber-demo&lang=en", lang="en"
        )
        self.assertIn("Framework coverage", html)
        self.assertIn("CTRL-IAM-001", html)
        gaps_html = ux_pages.gaps_page(
            build_gap_rows(self.michele),
            "superuser=1&program_id=program-cyber-demo&lang=en",
            {
                "lang": "en",
                "superuser": "1",
                "program_id": "program-cyber-demo",
                "framework": "",
                "status": "",
                "owner": "",
                "priority": "",
                "deadline_before": "",
                "deadline_after": "",
                "mapped": "",
                "missing_evidence": "",
                "search": "",
                "actor_tenants": "",
            },
            lang="en",
        )
        self.assertIn("/control?", gaps_html)
        self.assertIn("CTRL-IAM-001", gaps_html)
        self.assertIn("deadline_before", gaps_html)

    def test_owner_deadline_evidence_task_views(self):
        owners = owner_view(self.michele)
        self.assertIn("admin@wayfold.local", owners)
        self.assertIn("(unassigned)", owners)

        deadlines = deadline_view(self.michele, as_of=AS_OF)
        self.assertTrue(any(d.control_ref == "CTRL-IAM-002" for d in deadlines))

        evidence = evidence_view(self.michele)
        missing = [e for e in evidence if e.missing]
        self.assertTrue(missing)

        tasks = task_view(self.alfa, as_of=AS_OF)
        self.assertTrue(tasks)
        self.assertTrue(any(t.overdue for t in tasks))
        self.assertEqual(sum(t.open_task_count for t in tasks), 2)

    def test_report_uses_pinned_program_data(self):
        html = report_html(self.michele, as_of=AS_OF, nav_qs="lang=it")
        self.assertIn("Michele Demo", html)
        self.assertIn("Cyber Compliance Demo", html)
        self.assertIn("Avanzamento framework", html)
        self.assertIn("Requisiti non mappati", html)
        self.assertIn("A.9.9", html)
        self.assertIn("wfToggleLang", html)
        self.assertIn("sidebar", html)
        self.assertIn("--wf-primary:#675cf2", html)

        csv_text = report_csv(self.alfa, as_of=AS_OF)
        self.assertIn("Cliente Alfa", csv_text)
        self.assertIn("CTRL-EPM-001", csv_text)
        self.assertIn("NIS2-SUPPLY", csv_text)

    def test_evidence_task_counts_match_source(self):
        evid = evidence_view(self.michele)
        by_ref = {e.control_ref: e.evidence_count for e in evid}
        self.assertEqual(by_ref["CTRL-IAM-001"], 1)
        self.assertEqual(by_ref["CTRL-IR-001"], 0)

        tasks_m = task_view(self.michele, as_of=AS_OF)
        self.assertEqual(sum(t.open_task_count for t in tasks_m), 1)

    def test_api_portfolio_tenant_isolation(self):
        captured: dict = {}

        class FakeHandler(Handler):
            def __init__(self, path: str):
                self.path = path
                self.wfile = mock.Mock()
                self.wfile.write = lambda b: captured.__setitem__("body", b)
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

        FakeHandler("/api/portfolio?actor_tenants=tenant-michele").do_GET()
        self.assertEqual(captured["status"], 200)
        rows = json.loads(captured["body"].decode())
        self.assertEqual({r["tenant_id"] for r in rows}, {"tenant-michele"})

        FakeHandler("/api/client?actor_tenants=tenant-michele&program_id=program-alfa-cloud").do_GET()
        self.assertEqual(captured["status"], 403)

        FakeHandler(
            "/api/gaps?actor_tenants=tenant-michele&program_id=program-cyber-demo&mapped=0"
        ).do_GET()
        self.assertEqual(captured["status"], 200)
        gaps = json.loads(captured["body"].decode())
        self.assertTrue(gaps)
        self.assertTrue(all(g["mapping"] == "UNMAPPED" for g in gaps))

        FakeHandler(
            "/api/control?actor_tenants=tenant-michele&program_id=program-cyber-demo"
            "&control_ref=CTRL-IAM-001"
        ).do_GET()
        self.assertEqual(captured["status"], 200)
        detail = json.loads(captured["body"].decode())
        self.assertEqual(detail["control_ref"], "CTRL-IAM-001")
        self.assertGreaterEqual(len(detail["framework_coverage"]), 2)

        FakeHandler(
            "/api/control?actor_tenants=tenant-alfa&program_id=program-cyber-demo"
            "&control_ref=CTRL-IAM-001"
        ).do_GET()
        self.assertEqual(captured["status"], 403)

    def test_program_scoped_nav_redirects_or_selects_client(self):
        """Sidebar links without program_id must not render the same empty shell."""
        from types import SimpleNamespace

        import engine.api as api_mod

        captured: dict = {}

        class FakeHandler(Handler):
            def __init__(self, path: str):
                self.path = path
                self.wfile = mock.Mock()
                self.wfile.write = lambda b: captured.__setitem__("body", b)
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

        one = [
            SimpleNamespace(
                tenant_id="tenant-michele",
                tenant_name="Michele",
                program_id="program-cyber-demo",
                program_name="Demo",
                frameworks=["NIS2"],
            )
        ]
        with mock.patch.object(api_mod, "_resolve_program", return_value=None):
            with mock.patch.object(api_mod, "build_portfolio", return_value=one):
                FakeHandler("/gaps?superuser=1&lang=it").do_GET()
        self.assertEqual(captured["status"], 302)
        self.assertIn("program_id=program-cyber-demo", captured["headers"]["Location"])

        two = one + [
            SimpleNamespace(
                tenant_id="tenant-alfa",
                tenant_name="Alfa",
                program_id="program-alfa-cloud",
                program_name="Cloud",
                frameworks=["ISO"],
            )
        ]
        with mock.patch.object(api_mod, "_resolve_program", return_value=None):
            with mock.patch.object(api_mod, "build_portfolio", return_value=two):
                FakeHandler("/tasks?superuser=1&lang=it").do_GET()
        self.assertEqual(captured["status"], 200)
        html = captured["body"].decode()
        self.assertIn("Seleziona un cliente", html)
        self.assertIn("Analisi" if False else "Attività", html)
        self.assertIn('href="/tasks?', html)


if __name__ == "__main__":
    unittest.main()

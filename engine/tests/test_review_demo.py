"""Acceptance tests for the WF_REVIEW_DEMO_2026 product-review dataset."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.checklist import build_unified_checklist
from engine.consultant_views import control_detail, evidence_view, task_view
from engine.domain import CoverageRelation, ImplementationStatus
from engine.gap_assessment import GapFilter, build_gap_rows, filter_gap_rows
from engine.portfolio import build_portfolio
from engine.program_loader import load_program_snapshot
from engine.seed_review_demo import (
    DATASET_MARKER,
    PSNC_01_DELTA,
    install_to_data_dir,
    write_fixtures,
)

AS_OF = date(2026, 8, 9)
REVIEW = ROOT / "engine" / "fixtures" / "review"
MICHELE = REVIEW / "michele_cyber_2026.json"


class ReviewDemoDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_fixtures(REVIEW)
        cls.michele = load_program_snapshot(MICHELE)
        cls.checklist = build_unified_checklist(cls.michele)

    def test_marker_and_five_clients_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = install_to_data_dir(Path(tmp))
            self.assertEqual(result["clients"], 5)
            self.assertEqual(result["dataset_marker"], DATASET_MARKER)
            reg = json.loads((Path(tmp) / "portfolio_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(len(reg["programs"]), 5)
            rows = build_portfolio(
                actor_tenant_ids=set(),
                is_superuser=True,
                registry_path=Path(tmp) / "portfolio_registry.json",
                as_of=AS_OF,
            )
            self.assertEqual(len(rows), 5)
            names = {r.tenant_name for r in rows}
            self.assertIn("Michele S.r.l. [Demo]", names)
            self.assertTrue(all(r.critical_gaps >= 0 for r in rows))
            self.assertGreater(sum(r.overdue_tasks for r in rows), 0)
            self.assertGreater(sum(r.unmapped for r in rows), 0)

    def test_idempotent_safe_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Preserve a non-demo program
            other = {
                "tenant_id": "tenant-real",
                "tenant_name": "Cliente Reale",
                "program_id": "program-real",
                "program_name": "Real Program",
                "requirements": [],
                "implementations": [],
                "mappings": [],
            }
            (root / "programs").mkdir()
            (root / "programs" / "real.json").write_text(
                json.dumps(other), encoding="utf-8"
            )
            (root / "portfolio_registry.json").write_text(
                json.dumps({"programs": [{"snapshot": "programs/real.json"}]}),
                encoding="utf-8",
            )
            install_to_data_dir(root)
            install_to_data_dir(root)
            reg = json.loads((root / "portfolio_registry.json").read_text(encoding="utf-8"))
            snaps = [e["snapshot"] for e in reg["programs"]]
            self.assertEqual(snaps.count("programs/real.json"), 1)
            self.assertEqual(sum(1 for s in snaps if "michele" in s), 1)
            self.assertTrue((root / "programs" / "real.json").is_file())

    def test_ctrl_iam_dedup_and_coverage(self):
        iam = [c for c in self.checklist.controls if c.canonical_control_ref == "CTRL-IAM-001"]
        self.assertEqual(len(iam), 1)
        ctrl = iam[0]
        self.assertEqual(ctrl.status, ImplementationStatus.IN_PROGRESS)
        self.assertEqual(ctrl.owner, "Luca Rinaldi")
        self.assertEqual(ctrl.due_date, "2026-08-07")
        by_fw = {(c.framework_name, c.requirement_code, c.relation) for c in ctrl.framework_coverage}
        self.assertIn(("ISO/IEC 27001", "ISO-A.5.15", CoverageRelation.FULL), by_fw)
        self.assertIn(("ISO/IEC 27001", "ISO-A.5.18", CoverageRelation.FULL), by_fw)
        self.assertIn(("NIS2 Italia", "NIS2-01", CoverageRelation.FULL), by_fw)
        self.assertIn(("PSNC", "PSNC-01", CoverageRelation.PARTIAL), by_fw)
        partial = [c for c in ctrl.framework_coverage if c.relation == CoverageRelation.PARTIAL]
        self.assertTrue(any(PSNC_01_DELTA in (c.uncovered_delta or "") for c in partial))

    def test_all_four_implementation_statuses(self):
        statuses = {c.status for c in self.checklist.controls}
        self.assertEqual(
            statuses,
            {
                ImplementationStatus.IMPLEMENTED,
                ImplementationStatus.IN_PROGRESS,
                ImplementationStatus.NOT_IMPLEMENTED,
                ImplementationStatus.NOT_APPLICABLE,
            },
        )

    def test_unmapped_psnc06(self):
        codes = {u.code for u in self.checklist.unmapped}
        self.assertIn("PSNC-06", codes)

    def test_na_rationale_visible(self):
        detail = control_detail(self.michele, "CTRL-VULN-001")
        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(detail.status, "NOT_APPLICABLE")
        self.assertIn("fuori dal perimetro", detail.not_applicable_rationale)

    def test_evidence_reuse_and_tasks(self):
        evid = evidence_view(self.michele)
        shared = [e for e in evid if e.shared]
        self.assertTrue(shared)
        titles = {e.name for e in evid}
        self.assertIn("Access Control Policy v4", titles)
        detail = control_detail(self.michele, "CTRL-IAM-001")
        assert detail is not None
        self.assertGreaterEqual(len(detail.evidence_titles), 3)
        tasks = task_view(self.michele, as_of=AS_OF)
        self.assertGreaterEqual(len(tasks), 8)
        overdue = [t for t in tasks if t.overdue]
        self.assertTrue(any(t.task_id == "TASK-001" for t in overdue))

    def test_gaps_include_required_types(self):
        gaps = build_gap_rows(self.michele)
        unmapped = filter_gap_rows(gaps, GapFilter(mapped=False))
        self.assertTrue(any(g.requirement_code == "PSNC-06" for g in unmapped))
        partial = [g for g in gaps if g.mapping == "PARTIAL" and g.requirement_code == "PSNC-01"]
        self.assertTrue(partial)
        self.assertTrue(any("trimestrale" in (g.gap or "") for g in partial))
        impl_gap = [
            g
            for g in gaps
            if g.canonical_control_ref == "CTRL-SUP-001" and g.status == "NOT_IMPLEMENTED"
        ]
        self.assertTrue(impl_gap)

    def test_partial_not_promoted_when_implemented(self):
        # Temporarily treat IAM as IMPLEMENTED — PARTIAL must stay PARTIAL.
        impls = []
        for i in self.michele.implementations:
            if i.canonical_control_ref == "CTRL-IAM-001":
                impls.append(replace(i, status=ImplementationStatus.IMPLEMENTED))
            else:
                impls.append(i)
        program = replace(self.michele, implementations=impls)
        checklist = build_unified_checklist(program)
        from engine.readiness import framework_readiness

        rows = framework_readiness(program, checklist)
        psnc = next(r for r in rows if r.framework_name == "PSNC")
        self.assertGreaterEqual(psnc.partially_covered, 1)

    def test_tenant_isolation_portfolio(self):
        with tempfile.TemporaryDirectory() as tmp:
            install_to_data_dir(Path(tmp))
            rows = build_portfolio(
                actor_tenant_ids={"tenant-michele-demo"},
                is_superuser=False,
                registry_path=Path(tmp) / "portfolio_registry.json",
                as_of=AS_OF,
            )
            self.assertEqual({r.tenant_id for r in rows}, {"tenant-michele-demo"})

    def test_api_michele_workflow_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            install_to_data_dir(Path(tmp))
            reg = Path(tmp) / "portfolio_registry.json"
            from engine import ux_pages
            from engine.portfolio import build_client_dashboard

            rows = build_portfolio(
                actor_tenant_ids=set(),
                is_superuser=True,
                registry_path=reg,
                as_of=AS_OF,
            )
            self.assertEqual(len(rows), 5)
            html = ux_pages.portfolio_page(rows, "superuser=1&lang=it", lang="it")
            self.assertIn("Michele S.r.l. [Demo]", html)

            dash = build_client_dashboard(self.michele, as_of=AS_OF)
            client_html = ux_pages.client_page(
                dash, "program_id=program-michele-cyber-2026&lang=it", lang="it"
            )
            self.assertIn("Cyber Compliance 2026", client_html)
            self.assertIn("NIS2", client_html)
            self.assertIn("Nuova versione", client_html)

            detail = control_detail(self.michele, "CTRL-IAM-001")
            ctrl_html = ux_pages.control_page(
                detail,
                "program_id=program-michele-cyber-2026&lang=it",
                lang="it",
            )
            self.assertIn("CTRL-IAM-001", ctrl_html)
            self.assertIn("Luca Rinaldi", ctrl_html)
            self.assertTrue("PARTIAL" in ctrl_html.upper() or "Parziale" in ctrl_html)
            self.assertIn("trimestrale", ctrl_html)
            self.assertIn("Access Control Policy", ctrl_html)


if __name__ == "__main__":
    unittest.main()

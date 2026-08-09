"""UI design system / Italian localization smoke tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.i18n import NAV_SECTIONS, t
from engine.program_loader import load_program_snapshot
from engine.ui_icons import PATH_ICONS, icon, icon_for_path
from engine.ui_labels import mapping_label, status_label, status_variant
from engine.ui_shell import WAYFOLD_CSS, render_shell
from engine import ux_pages
from engine.gap_assessment import build_gap_rows
from engine.portfolio import build_portfolio

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MICHELE = FIXTURES / "michele_phase2_program.json"


class UiDesignSystemTests(unittest.TestCase):
    def test_tokens_and_shell_sidebar(self):
        html = render_shell("Portfolio", "superuser=1&lang=it", "<p>ok</p>", active_path="/portfolio")
        self.assertIn("--wf-primary:#675cf2", html)
        self.assertIn("--wf-sidebar:#101522", html)
        self.assertIn('class="sidebar"', html)
        self.assertIn('class="nav-item active"', html)
        self.assertIn("/portfolio", html)
        self.assertIn("Area di lavoro", html)
        self.assertIn("Knowledge Base", html)
        self.assertIn("Amministrazione", html)
        self.assertIn("viewBox=", html)
        self.assertNotIn("--acc:#d97b5c", html)
        self.assertIn(WAYFOLD_CSS[:20], html)

    def test_nav_icons_are_svg_not_numbers(self):
        for _section, entries in NAV_SECTIONS:
            for _key, path, _icon in entries:
                svg = icon_for_path(path)
                self.assertIn("<svg", svg)
                self.assertIn("viewBox=", svg)
                self.assertTrue(path in PATH_ICONS)

    def test_status_labels_italian(self):
        self.assertEqual(status_label("it", "IMPLEMENTED"), "Implementato")
        self.assertEqual(status_label("it", "IN_PROGRESS"), "In corso")
        self.assertEqual(status_label("it", "NOT_IMPLEMENTED"), "Non implementato")
        self.assertEqual(mapping_label("it", "PARTIAL"), "Parziale")
        self.assertEqual(status_variant("IMPLEMENTED"), "success")
        self.assertEqual(t("it", "nav.checklist"), "Controlli unificati")
        self.assertEqual(t("it", "nav.gaps"), "Analisi dei gap")

    def test_icon_helper_unknown_falls_back(self):
        svg = icon("does-not-exist")
        self.assertIn("<svg", svg)

    def test_portfolio_and_gaps_render_italian(self):
        rows = build_portfolio(actor_tenant_ids=set(), is_superuser=True)
        html = ux_pages.portfolio_page(rows, "superuser=1&lang=it", lang="it")
        self.assertIn("Portfolio", html)
        self.assertIn("Clienti attivi", html)
        self.assertIn("nav-icon", html)
        program = load_program_snapshot(MICHELE)
        gaps_html = ux_pages.gaps_page(
            build_gap_rows(program),
            "superuser=1&program_id=program-cyber-demo&lang=it",
            {
                "lang": "it",
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
            lang="it",
        )
        self.assertIn("Analisi dei gap", gaps_html)
        self.assertIn("Implementato", gaps_html)
        self.assertNotIn("←", gaps_html)


if __name__ == "__main__":
    unittest.main()

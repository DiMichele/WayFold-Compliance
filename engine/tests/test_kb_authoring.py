"""Critical Knowledge Base authoring E2E (isolated data dir)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class KbAuthoringE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        os.environ["WAYFOLD_DATA_DIR"] = str(self.data)
        os.environ["WAYFOLD_OPEN_ACCESS"] = "0"
        os.environ["WAYFOLD_ALLOW_QS_AUTH"] = "1"
        os.environ["WAYFOLD_SEED_DEMO"] = "0"
        # Fresh module state for data_root
        import importlib
        import engine.runtime_paths as rp
        import engine.framework_versions as fv
        import engine.framework_registry as fr
        import engine.control_catalog as cc
        import engine.kb_mappings as km

        importlib.reload(rp)
        importlib.reload(fv)
        importlib.reload(fr)
        importlib.reload(cc)
        importlib.reload(km)

        # Minimal empty registry
        reg = self.data / "portfolio_registry.json"
        reg.write_text(json.dumps({"programs": []}, indent=2) + "\n", encoding="utf-8")
        os.environ["WAYFOLD_PORTFOLIO_REGISTRY"] = str(reg)

        from engine.api import Handler
        from http.server import ThreadingHTTPServer
        import threading

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.tmp.cleanup()
        for key in (
            "WAYFOLD_DATA_DIR",
            "WAYFOLD_PORTFOLIO_REGISTRY",
            "WAYFOLD_ALLOW_QS_AUTH",
            "WAYFOLD_SEED_DEMO",
        ):
            os.environ.pop(key, None)

    def _url(self, path: str) -> str:
        sep = "&" if "?" in path else "?"
        return f"{self.base}{path}{sep}superuser=1&lang=it"

    def _get(self, path: str):
        import urllib.request

        req = urllib.request.Request(self._url(path))
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")

    def _post(self, path: str, data: dict[str, str], *, follow: bool = False):
        import urllib.parse
        import urllib.request

        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(
            self._url(path),
            data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.geturl(), resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            if exc.code in {302, 303} and not follow:
                loc = exc.headers.get("Location") or ""
                return exc.code, loc, ""
            raise

    def test_authoring_create_map_publish_immutable_assign(self):
        import urllib.error
        import urllib.parse
        import urllib.request

        # 1) Create framework + first draft version
        status, loc, _ = self._post(
            "/frameworks/new",
            {
                "name": "Regolamento Cyber Demo XYZ",
                "short_name": "Cyber Demo XYZ",
                "type": "Normativa",
                "publisher": "WayFold Demo",
                "jurisdiction": "IT",
                "language": "it",
                "description": "Framework demo authoring",
                "official_url": "https://example.test/xyz",
                "version_label": "1.0",
            },
        )
        self.assertIn(status, {200, 302, 303})
        # Follow redirect manually if needed
        if status in {302, 303} and loc:
            path = urlparse(loc).path + ("?" + urlparse(loc).query if urlparse(loc).query else "")
        else:
            # parse from page
            st, html = self._get("/frameworks")
            self.assertEqual(st, 200)
            self.assertIn("Regolamento Cyber Demo XYZ", html)
            path = "/frameworks"

        st, html = self._get("/frameworks")
        self.assertEqual(st, 200)
        self.assertIn("Regolamento Cyber Demo XYZ", html)
        self.assertIn("Bozza", html)
        self.assertIn("Normativa", html)

        from engine import framework_versions as fv
        from engine import framework_registry as fr

        fws = fr.list_frameworks()
        self.assertTrue(fws)
        fw = next(f for f in fws if "XYZ" in f.name)
        versions = fv.list_versions(framework_id=fw.id)
        self.assertEqual(len(versions), 1)
        ver = versions[0]
        self.assertEqual(ver.status, "DRAFT")
        self.assertEqual(ver.version, "1.0")

        # 2) Requirements
        for code, title in [
            ("XYZ-01", "Gestione degli accessi"),
            ("XYZ-02", "Gestione degli incidenti"),
            ("XYZ-03", "Continuità operativa"),
            ("XYZ-04", "Requisito non mappato"),
        ]:
            st, loc, _ = self._post(
                "/frameworks/requirements/new",
                {
                    "version_id": ver.id,
                    "code": code,
                    "title": title,
                    "description": title,
                    "req_type": "Requisito",
                    "section": "Demo",
                    "order": "0",
                },
            )
            self.assertIn(st, {200, 302, 303}, msg=f"{code} -> {st}")

        ver = fv.get_version(ver.id)
        self.assertEqual(len(ver.requirements), 4)

        # 3) Controls
        from engine import control_catalog as cc

        st, loc, _ = self._post(
            "/controls/new",
            {
                "code": "CTRL-DEMO-ACCESS",
                "title": "Gestione degli accessi demo",
                "domain": "Accesso",
                "description": "Controllo accessi demo",
                "default_priority": "HIGH",
            },
        )
        self.assertIn(st, {200, 302, 303})
        st, loc, _ = self._post(
            "/controls/new",
            {
                "code": "CTRL-DEMO-IR",
                "title": "Gestione incidenti demo",
                "domain": "Incidenti",
                "description": "IR demo",
                "default_priority": "HIGH",
            },
        )
        self.assertIn(st, {200, 302, 303})
        # Existing BCP control for PARTIAL
        cc.create_control(
            code="CTRL-BCP-001",
            title="Continuità operativa",
            domain="Continuità",
        )

        reqs = {r.code: r for r in ver.requirements}
        # 4) Mappings
        from engine import kb_mappings as km
        from engine.domain import CoverageRelation, MappingRecord, ReviewStatus

        km.upsert_mapping(
            MappingRecord(
                requirement_id=reqs["XYZ-01"].id,
                framework_id=fw.id,
                framework_name=fw.name,
                framework_version="1.0",
                requirement_code="XYZ-01",
                canonical_control_id="CTRL-DEMO-ACCESS",
                canonical_control_ref="CTRL-DEMO-ACCESS",
                relation=CoverageRelation.FULL,
                rationale="Copertura completa accessi",
                review_status=ReviewStatus.APPROVED,
            )
        )
        km.upsert_mapping(
            MappingRecord(
                requirement_id=reqs["XYZ-02"].id,
                framework_id=fw.id,
                framework_name=fw.name,
                framework_version="1.0",
                requirement_code="XYZ-02",
                canonical_control_id="CTRL-DEMO-IR",
                canonical_control_ref="CTRL-DEMO-IR",
                relation=CoverageRelation.FULL,
                rationale="Copertura completa incidenti",
                review_status=ReviewStatus.APPROVED,
            )
        )
        km.upsert_mapping(
            MappingRecord(
                requirement_id=reqs["XYZ-03"].id,
                framework_id=fw.id,
                framework_name=fw.name,
                framework_version="1.0",
                requirement_code="XYZ-03",
                canonical_control_id="CTRL-BCP-001",
                canonical_control_ref="CTRL-BCP-001",
                relation=CoverageRelation.PARTIAL,
                uncovered_delta="È richiesto un test specifico annuale.",
                rationale="Copertura parziale continuità",
                review_status=ReviewStatus.APPROVED,
            )
        )
        # PARTIAL without delta must fail
        with self.assertRaises(ValueError):
            km.upsert_mapping(
                MappingRecord(
                    requirement_id=reqs["XYZ-04"].id,
                    framework_id=fw.id,
                    framework_name=fw.name,
                    framework_version="1.0",
                    requirement_code="XYZ-04",
                    canonical_control_id="CTRL-BCP-001",
                    canonical_control_ref="CTRL-BCP-001",
                    relation=CoverageRelation.PARTIAL,
                    uncovered_delta="",
                )
            )

        summary = km.coverage_summary(ver.requirements, km.list_mappings(framework_version="1.0"))
        self.assertEqual(summary["total_requirements"], 4)
        self.assertEqual(summary["full"], 2)
        self.assertEqual(summary["partial"], 1)
        self.assertEqual(summary["unmapped"], 1)

        # 5) Publish with confirmation
        st, loc, _ = self._post(
            "/frameworks/publish",
            {"version_id": ver.id, "confirm": "1"},
        )
        self.assertIn(st, {200, 302, 303})
        ver = fv.get_version(ver.id)
        self.assertEqual(ver.status, "PUBLISHED")

        # 6) Immutability
        with self.assertRaises(fv.ImmutabilityError):
            fv.update_requirement(ver.id, reqs["XYZ-01"].id, {"title": "HACK"})

        draft = fv.clone_draft(ver.id, new_version="1.1")
        self.assertEqual(draft.status, "DRAFT")
        fv.add_requirement(draft.id, code="XYZ-05", title="Nuovo in bozza")
        self.assertTrue(any(r.code == "XYZ-05" for r in fv.get_version(draft.id).requirements))

        # 7) Client + program + checklist dedup
        from engine import program_authoring as pa

        client = pa.create_client_shell(name="Demo Authoring Client", code="demo-auth")
        # Second published framework: clone publish a tiny one
        fw2 = fr.create_framework(
            name="Standard Demo Extra",
            type="Standard",
            publisher="WayFold Demo",
        )
        v2 = fv.create_version(
            framework_id=fw2.id,
            framework_name=fw2.name,
            publisher=fw2.publisher,
            version="2026",
        )
        r_a = fv.add_requirement(v2.id, code="EXT-01", title="Accesso extra")
        km.upsert_mapping(
            MappingRecord(
                requirement_id=r_a.id,
                framework_id=fw2.id,
                framework_name=fw2.name,
                framework_version="2026",
                requirement_code="EXT-01",
                canonical_control_id="CTRL-DEMO-ACCESS",
                canonical_control_ref="CTRL-DEMO-ACCESS",
                relation=CoverageRelation.FULL,
                review_status=ReviewStatus.APPROVED,
            )
        )
        fv.publish_version(v2.id)

        program = pa.create_program(
            name="Demo Compliance Program",
            tenant_id=client["tenant_id"],
            tenant_name=client["tenant_name"],
            scope="Demo scope",
            owner="Consulente Demo",
            version_ids=[ver.id, v2.id],
            registry_path=Path(os.environ["WAYFOLD_PORTFOLIO_REGISTRY"]),
        )
        from engine.checklist import build_unified_checklist

        checklist = build_unified_checklist(program)
        access_rows = [
            c for c in checklist.controls if c.canonical_control_ref == "CTRL-DEMO-ACCESS"
        ]
        self.assertEqual(len(access_rows), 1, "shared control must be deduplicated")
        self.assertGreaterEqual(len(checklist.controls), 2)
        self.assertTrue(any(u.code == "XYZ-04" for u in checklist.unmapped))

        st, html = self._get("/controls")
        self.assertEqual(st, 200)
        self.assertIn("CTRL-DEMO-ACCESS", html)
        self.assertIn("Catalogo controlli", html)

        st, html = self._get("/frameworks")
        self.assertIn("Framework e normative", html)
        # EN language switch removed from sidebar
        st, html = self._get("/portfolio")
        self.assertNotIn(">EN</span>", html)
        self.assertNotIn("onclick=\"wfToggleLang", html)
        self.assertIn("+ Nuovo", html)


if __name__ == "__main__":
    unittest.main()

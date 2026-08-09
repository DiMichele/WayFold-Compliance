"""P0 security + gap/mapping realignment tests (SEC-* / GAP-* / MAP-*)."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api import Handler
from engine.auth_session import issue_session
from engine.checklist import build_unified_checklist
from engine.csrf import issue_csrf_token, validate_csrf
from engine.domain import (
    CoverageRelation,
    ImplementationStatus,
    MappingRecord,
    ReviewStatus,
)
from engine.gap_assessment import GapTaxonomy, build_gap_rows, gap_counters
from engine.program_loader import load_program_snapshot
from engine.rbac import (
    PERM_CONTROL_WRITE,
    PERM_EVIDENCE_WRITE,
    PERM_TASK_WRITE,
    Role,
    has_permission,
)
from engine.users import create_user, seed_rbac_test_users


FIXTURES = ROOT / "engine" / "fixtures"


class FakeHandler(Handler):
    def __init__(self, path: str, *, cookie: str = "", body: bytes = b"", method: str = "GET"):
        self.path = path
        self.command = method
        self.headers = {
            "Cookie": cookie,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
            "Host": "localhost",
        }
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status = 0
        self._headers_out: list[tuple[str, str]] = []
        self.client_address = ("127.0.0.1", 12345)

    def send_response(self, code, message=None):  # noqa: ARG002
        self.status = code

    def send_header(self, key, value):
        self._headers_out.append((key, value))

    def end_headers(self):
        pass


class SecurityRealignmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.env = {
            "WAYFOLD_DATA_DIR": str(self.data),
            "WAYFOLD_SESSION_SECRET": "test-secret-realign",
            "WAYFOLD_OPEN_ACCESS": "0",
            "WAYFOLD_ALLOW_QS_AUTH": "0",
            "WAYFOLD_SEED_DEMO": "0",
            "WAYFOLD_TEST_MODE": "1",
            "WAYFOLD_CSRF_DISABLE": "1",
            "WAYFOLD_MFA_ENFORCE": "0",
            "WAYFOLD_AUTH_USER": "admin",
            "WAYFOLD_AUTH_PASSWORD": "admin",
        }
        self._patch = mock.patch.dict(os.environ, self.env, clear=False)
        self._patch.start()
        seed_rbac_test_users(password="test-pass-xyz")
        # Install Michele program
        from engine.seed_review_demo import install_to_data_dir

        try:
            install_to_data_dir(self.data)
        except Exception:
            # Fallback: copy fixture
            prog = FIXTURES / "review" / "michele_cyber_2026.json"
            if not prog.is_file():
                prog = FIXTURES / "michele_phase2_program.json"
            (self.data / "programs").mkdir(parents=True, exist_ok=True)
            dest = self.data / "programs" / "michele.json"
            dest.write_text(prog.read_text(encoding="utf-8"), encoding="utf-8")
            (self.data / "portfolio_registry.json").write_text(
                json.dumps({"programs": [{"snapshot": str(dest), "program_id": "program-michele-cyber-2026"}]}),
                encoding="utf-8",
            )

    def tearDown(self):
        self._patch.stop()
        self.tmp.cleanup()

    def _cookie(self, role: Role, tenants: list[str], username: str = "u") -> str:
        tok = issue_session(username, role=role, tenant_ids=tenants)
        return f"wf_session={tok}"

    def test_SEC_CTRL_01_viewer_denied_control_update(self):
        self.assertFalse(has_permission(Role.VIEWER, PERM_CONTROL_WRITE))
        cookie = self._cookie(Role.VIEWER, ["tenant-michele-demo"], "viewer_michele")
        from engine.portfolio import load_portfolio_programs

        programs = load_portfolio_programs(self.data / "portfolio_registry.json")
        self.assertTrue(programs)
        pid = programs[0][0].program_id
        payload = json.dumps(
            {
                "control_id": "CTRL-IAM-001",
                "expected_version": 1,
                "status": "IMPLEMENTED",
            }
        ).encode()
        h = FakeHandler(
            f"/api/control/update?program_id={pid}",
            cookie=cookie,
            body=payload,
            method="POST",
        )
        h.do_POST()
        self.assertEqual(h.status, 403)

    def test_SEC_CTRL_02_member_cross_tenant_denied(self):
        cookie = self._cookie(
            Role.CLIENT_MEMBER, ["tenant-michele-demo"], "client_member_michele"
        )
        # Resolve alfa program id if present
        payload = json.dumps(
            {
                "control_id": "CTRL-IAM-001",
                "expected_version": 1,
                "status": "IMPLEMENTED",
            }
        ).encode()
        h = FakeHandler(
            "/api/control/update?program_id=program-alfa-cloud-2026",
            cookie=cookie,
            body=payload,
            method="POST",
        )
        h.do_POST()
        self.assertIn(h.status, {403, 404})

    def test_SEC_GET_01_state_changing_get_denied(self):
        cookie = self._cookie(Role.SUPER_ADMIN, [], "superadmin_test")
        for path in (
            "/api/frameworks/publish?version_id=x",
            "/api/frameworks/clone?version_id=x&new_version=2",
            "/api/frameworks/patch?version_id=x",
            "/api/regulatory/check?source_id=x",
            "/api/regulatory/review?change_id=x&status=ACCEPTED",
            "/api/auto-evidence/ingest?connector_id=x",
            "/api/auto-evidence/review?evidence_id=x&status=APPROVED",
        ):
            h = FakeHandler(path, cookie=cookie)
            h.do_GET()
            self.assertIn(h.status, {404, 405}, msg=path)

    def test_SEC_SET_01_client_admin_no_global_users(self):
        cookie = self._cookie(
            Role.CLIENT_ADMIN, ["tenant-michele-demo"], "client_admin_michele"
        )
        h = FakeHandler("/api/settings", cookie=cookie)
        h.do_GET()
        self.assertEqual(h.status, 403)

    def test_SEC_CSRF_01_missing_token_denied(self):
        os.environ["WAYFOLD_CSRF_DISABLE"] = "0"
        os.environ["WAYFOLD_CSRF_ENFORCE_IN_TEST"] = "1"
        try:
            err = validate_csrf(
                method="POST",
                cookie_token=None,
                form_token=None,
                header_token=None,
                origin="http://localhost",
                referer=None,
                host="localhost",
            )
            self.assertEqual(err, "csrf_missing")
            tok = issue_csrf_token()
            err2 = validate_csrf(
                method="POST",
                cookie_token=tok,
                form_token=tok,
                header_token=None,
                origin="http://evil.example",
                referer=None,
                host="localhost",
            )
            self.assertEqual(err2, "csrf_bad_origin")
            err3 = validate_csrf(
                method="POST",
                cookie_token=tok,
                form_token=tok,
                header_token=None,
                origin="http://localhost",
                referer=None,
                host="localhost",
            )
            self.assertIsNone(err3)
        finally:
            os.environ["WAYFOLD_CSRF_DISABLE"] = "1"
            os.environ.pop("WAYFOLD_CSRF_ENFORCE_IN_TEST", None)

    def test_GAP_01_partial_delta_isolation(self):
        # Synthetic program: ISO FULL, NIS2 FULL, PSNC PARTIAL → same CTRL
        base = load_program_snapshot(FIXTURES / "michele_phase2_program.json")
        maps = [
            MappingRecord(
                requirement_id="req-iso",
                framework_id="iso",
                framework_name="ISO/IEC 27001",
                framework_version="2022",
                requirement_code="ISO-A.5.15",
                canonical_control_id="CTRL-IAM-001",
                canonical_control_ref="CTRL-IAM-001",
                relation=CoverageRelation.FULL,
                review_status=ReviewStatus.APPROVED,
            ),
            MappingRecord(
                requirement_id="req-nis2",
                framework_id="nis2",
                framework_name="NIS2 Italia",
                framework_version="2026.1",
                requirement_code="NIS2-01",
                canonical_control_id="CTRL-IAM-001",
                canonical_control_ref="CTRL-IAM-001",
                relation=CoverageRelation.FULL,
                review_status=ReviewStatus.APPROVED,
            ),
            MappingRecord(
                requirement_id="req-psnc",
                framework_id="psnc",
                framework_name="PSNC",
                framework_version="2024",
                requirement_code="PSNC-01",
                canonical_control_id="CTRL-IAM-001",
                canonical_control_ref="CTRL-IAM-001",
                relation=CoverageRelation.PARTIAL,
                uncovered_delta="Revisione trimestrale asset critici",
                review_status=ReviewStatus.APPROVED,
            ),
        ]
        # Minimal requirements + one implemented control
        from engine.domain import (
            ControlImplementationSnapshot,
            RequirementSnapshot,
        )

        reqs = [
            RequirementSnapshot(
                id="req-iso",
                framework_id="iso",
                framework_name="ISO/IEC 27001",
                framework_version="2022",
                code="ISO-A.5.15",
                title="IAM",
            ),
            RequirementSnapshot(
                id="req-nis2",
                framework_id="nis2",
                framework_name="NIS2 Italia",
                framework_version="2026.1",
                code="NIS2-01",
                title="IAM",
            ),
            RequirementSnapshot(
                id="req-psnc",
                framework_id="psnc",
                framework_name="PSNC",
                framework_version="2024",
                code="PSNC-01",
                title="IAM",
            ),
        ]
        impls = [
            ControlImplementationSnapshot(
                id="impl-iam",
                ref_id="CTRL-IAM-001",
                name="IAM",
                canonical_control_id="CTRL-IAM-001",
                canonical_control_ref="CTRL-IAM-001",
                status=ImplementationStatus.IMPLEMENTED,
                evidence_count=2,
            )
        ]
        program = replace(
            base,
            requirements=reqs,
            mappings=maps,
            implementations=impls,
            requirement_implementation_links={
                "req-iso": ["impl-iam"],
                "req-nis2": ["impl-iam"],
                "req-psnc": ["impl-iam"],
            },
            tasks=[],
            evidences=[],
        )
        rows = build_gap_rows(program)
        partial = [
            r
            for r in rows
            if r.taxonomy == GapTaxonomy.PARTIAL_COVERAGE
        ]
        self.assertTrue(any(r.requirement_code == "PSNC-01" for r in partial))
        self.assertFalse(
            any(r.requirement_code == "ISO-A.5.15" and r.taxonomy == GapTaxonomy.PARTIAL_COVERAGE for r in rows)
        )
        self.assertFalse(
            any(r.requirement_code == "NIS2-01" and r.taxonomy == GapTaxonomy.PARTIAL_COVERAGE for r in rows)
        )
        for r in partial:
            if r.requirement_code == "PSNC-01":
                self.assertIn("trimestrale", r.gap.lower())
            self.assertNotIn("gap_notes_aggregate", r.gap)

    def test_MAP_01_draft_excluded_from_readiness(self):
        from engine.readiness import framework_readiness

        base = load_program_snapshot(FIXTURES / "michele_phase2_program.json")
        before = framework_readiness(base)
        # Add DRAFT FULL mapping for an unmapped req if any
        unmapped_before = build_unified_checklist(base).unmapped
        if not unmapped_before:
            self.skipTest("no unmapped requirements in fixture")
        u = unmapped_before[0]
        draft = MappingRecord(
            requirement_id=u.requirement_id,
            framework_id=u.framework_id,
            framework_name=u.framework_name,
            framework_version=u.framework_version,
            requirement_code=u.code,
            canonical_control_id="CTRL-IAM-001",
            canonical_control_ref="CTRL-IAM-001",
            relation=CoverageRelation.FULL,
            review_status=ReviewStatus.DRAFT,
        )
        program = replace(base, mappings=list(base.mappings) + [draft])
        after = framework_readiness(program)
        # Unmapped count for that framework should be unchanged
        b = {r.framework_id: r.unmapped for r in before}
        a = {r.framework_id: r.unmapped for r in after}
        self.assertEqual(b.get(u.framework_id), a.get(u.framework_id))

    def test_MAP_02_no_implicit_full(self):
        from engine.domain import (
            ControlImplementationSnapshot,
            RequirementSnapshot,
        )

        req = RequirementSnapshot(
            id="r1",
            framework_id="fw",
            framework_name="FW",
            framework_version="1",
            code="R-1",
            title="Req",
        )
        impl = ControlImplementationSnapshot(
            id="i1",
            ref_id="CTRL-X",
            name="X",
            canonical_control_id="CTRL-X",
            canonical_control_ref="CTRL-X",
            status=ImplementationStatus.IMPLEMENTED,
        )
        from engine.domain import ProgramSnapshot

        program = ProgramSnapshot(
            tenant_id="t",
            tenant_name="T",
            program_id="p",
            program_name="P",
            requirements=[req],
            implementations=[impl],
            mappings=[],
            requirement_implementation_links={"r1": ["i1"]},
        )
        cl = build_unified_checklist(program)
        # Must not be FULL
        for c in cl.controls:
            for cov in c.framework_coverage:
                self.assertNotEqual(cov.relation, CoverageRelation.FULL)
                self.assertEqual(cov.relation, CoverageRelation.NEEDS_REVIEW)
        from engine.readiness import framework_readiness

        rows = framework_readiness(program, cl)
        self.assertEqual(rows[0].fully_covered, 0)

    def test_GAP_02_counters_are_distinct_requirements(self):
        program = load_program_snapshot(FIXTURES / "michele_phase2_program.json")
        rows = build_gap_rows(program)
        counters = gap_counters(rows)
        self.assertEqual(counters.findings_total, len(rows))
        self.assertEqual(
            counters.requirements_with_problems,
            len({r.requirement_id for r in rows}),
        )
        # Every finding must carry a real taxonomy; no empty "coverage echo" rows
        for r in rows:
            self.assertIn(
                r.taxonomy,
                {
                    GapTaxonomy.PARTIAL_COVERAGE,
                    GapTaxonomy.IMPLEMENTATION,
                    GapTaxonomy.EVIDENCE,
                    GapTaxonomy.REMEDIATION,
                    GapTaxonomy.UNMAPPED,
                },
            )
            if r.taxonomy == GapTaxonomy.PARTIAL_COVERAGE:
                self.assertTrue((r.gap or "").strip())


if __name__ == "__main__":
    unittest.main()

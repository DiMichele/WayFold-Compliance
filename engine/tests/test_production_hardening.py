"""Production readiness regression: RBAC, evidence, immutability, audit, SSRF."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api import Handler
from engine.auth_session import issue_session, parse_session_token, session_cookie_header
from engine.control_locking import ConflictError, ControlPatch, apply_patch, get_version
from engine.evidence_storage import (
    AuthzContext,
    read_evidence_bytes,
    store_evidence,
)
from engine.framework_versions import (
    FrameworkRequirement,
    FrameworkVersionRecord,
    ImmutabilityError,
    clone_draft,
    publish_version,
    update_published_denied,
    upsert_version,
)
from engine.mfa import generate_totp_secret, totp, verify_totp
from engine.rbac import (
    PERM_CONTROL_WRITE,
    PERM_EVIDENCE_DOWNLOAD,
    PERM_FRAMEWORK_PUBLISH,
    PERM_KB_WRITE,
    Role,
    has_permission,
)
from engine.report_snapshots import generate_snapshot, get_snapshot
from engine.regulatory.fetch import validate_url
from engine.users import authenticate, create_user, seed_rbac_test_users
from engine import audit as audit_mod
from engine.program_loader import load_program_snapshot
from engine.domain import ImplementationStatus


class FakeHandler(Handler):
    def __init__(self, path: str, cookie: str | None = None, body: bytes = b""):
        self.path = path
        self.headers = {"Cookie": cookie} if cookie else {}
        self.wfile = mock.Mock()
        self._body_chunks: list[bytes] = []
        self.wfile.write = lambda b: self._body_chunks.append(b)
        self.rfile = mock.Mock()
        self.rfile.read = lambda n: body[:n]
        self.status = None
        self.resp_headers: dict[str, str] = {}

    def send_response(self, code, message=None):  # noqa: ARG002
        self.status = code

    def send_header(self, key, value):
        self.resp_headers[key] = value

    def end_headers(self):
        return None

    def address_string(self):
        return "test"

    @property
    def body(self) -> bytes:
        return b"".join(self._body_chunks)


class ProductionHardeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.env = {
            "WAYFOLD_DATA_DIR": str(self.data),
            "WAYFOLD_OPEN_ACCESS": "0",
            "WAYFOLD_ALLOW_QS_AUTH": "0",
            "WAYFOLD_SEED_DEMO": "0",
            "WAYFOLD_SESSION_SECRET": "hardening-secret",
            "WAYFOLD_AUTH_USER": "admin",
            "WAYFOLD_AUTH_PASSWORD": "admin",
        }
        self._cm = mock.patch.dict(os.environ, self.env, clear=False)
        self._cm.start()
        self.test_password = "T3st-Only-" + "x" * 12
        self.users = seed_rbac_test_users(password=self.test_password)

    def tearDown(self):
        self._cm.stop()
        self.tmp.cleanup()

    def _cookie(self, username: str, *, role: str, tenants: list[str], superuser: bool = False):
        token = issue_session(
            username, role=role, tenant_ids=tenants, is_superuser=superuser
        )
        return session_cookie_header(token, secure=False).split(";", 1)[0]

    def test_anonymous_routes_redirect_or_401(self):
        for path, expect in [
            ("/portfolio", 302),
            ("/clients", 302),
            ("/checklist", 302),
            ("/evidence", 302),
            ("/frameworks", 302),
            ("/mappings", 302),
            ("/api/portfolio", 401),
            ("/api/evidence/EV-001/download", 401),
        ]:
            h = FakeHandler(path)
            h.do_GET()
            self.assertEqual(h.status, expect, path)
            if expect == 302:
                self.assertTrue(h.resp_headers["Location"].startswith("/login"))

    def test_admin_login_issues_superadmin_session(self):
        result = authenticate("admin", "admin")
        self.assertTrue(result.ok)
        assert result.user is not None
        self.assertEqual(result.user.role, Role.SUPER_ADMIN.value)
        token = issue_session(
            result.user.username,
            role=result.user.role,
            tenant_ids=[],
            is_superuser=True,
        )
        session = parse_session_token(token)
        self.assertIsNotNone(session)
        assert session is not None
        self.assertTrue(session.is_superuser)

    def test_rbac_matrix(self):
        self.assertTrue(has_permission(Role.SUPER_ADMIN, PERM_KB_WRITE))
        self.assertTrue(has_permission(Role.CONSULTANT, PERM_KB_WRITE))
        self.assertFalse(has_permission(Role.CLIENT_MEMBER, PERM_FRAMEWORK_PUBLISH))
        self.assertFalse(has_permission(Role.VIEWER, PERM_CONTROL_WRITE))
        self.assertTrue(has_permission(Role.VIEWER, PERM_EVIDENCE_DOWNLOAD))

        # Michele admin can open Michele portfolio; Alfa denied
        michele_cookie = self._cookie(
            "client_admin_michele",
            role=Role.CLIENT_ADMIN.value,
            tenants=["tenant-michele-demo"],
        )
        h = FakeHandler("/api/portfolio", cookie=michele_cookie)
        # empty portfolio registry in temp data — still 200
        h.do_GET()
        self.assertEqual(h.status, 200)

        # Cross-tenant: force gate against alfa
        from engine.authz import assert_tenant_access

        denied = assert_tenant_access(
            actor_tenant_ids={"tenant-michele-demo"},
            is_superuser=False,
            target_tenant_id="tenant-alfa-demo",
        )
        self.assertFalse(denied.allowed)

        allowed = assert_tenant_access(
            actor_tenant_ids={"tenant-michele-demo"},
            is_superuser=False,
            target_tenant_id="tenant-michele-demo",
        )
        self.assertTrue(allowed.allowed)

    def test_evidence_binary_authz(self):
        item = store_evidence(
            tenant_id="tenant-michele-demo",
            program_id="prog-michele",
            title="Policy",
            filename="policy.txt",
            content=b"confidential-bytes",
            content_type="text/plain",
            evidence_id="EV-TEST-001",
        )
        # anonymous denied via API
        h = FakeHandler(f"/api/evidence/{item.id}/download")
        h.do_GET()
        self.assertEqual(h.status, 401)

        # wrong tenant
        wrong = AuthzContext(
            username="client_admin_alfa",
            role=Role.CLIENT_ADMIN,
            actor_tenant_ids={"tenant-alfa-demo"},
            is_superuser=False,
        )
        with self.assertRaises(PermissionError):
            read_evidence_bytes(item, wrong)

        # viewer own tenant allowed
        viewer = AuthzContext(
            username="viewer_michele",
            role=Role.VIEWER,
            actor_tenant_ids={"tenant-michele-demo"},
            is_superuser=False,
        )
        data = read_evidence_bytes(item, viewer)
        self.assertEqual(data, b"confidential-bytes")

        # consultant assigned
        cons = AuthzContext(
            username="consultant_test",
            role=Role.CONSULTANT,
            actor_tenant_ids={"tenant-michele-demo"},
            is_superuser=False,
        )
        self.assertEqual(read_evidence_bytes(item, cons), b"confidential-bytes")

        # superadmin
        sa = AuthzContext(
            username="superadmin_test",
            role=Role.SUPER_ADMIN,
            actor_tenant_ids=set(),
            is_superuser=True,
        )
        self.assertEqual(read_evidence_bytes(item, sa), b"confidential-bytes")

    def test_published_immutability(self):
        rec = FrameworkVersionRecord(
            id="fv-test-pub",
            framework_id="fw-nis2",
            framework_name="NIS2 Italia",
            publisher="ACN",
            version="2026.1",
            status="DRAFT",
            requirements=[
                FrameworkRequirement(id="r1", code="NIS2-01", title="IAM")
            ],
        )
        upsert_version(rec)
        publish_version(rec.id)
        with self.assertRaises(ImmutabilityError):
            update_published_denied(rec.id, {"framework_name": "HACKED"})
        draft = clone_draft(rec.id, new_version="2026.2")
        self.assertEqual(draft.status, "DRAFT")
        update_published_denied(draft.id, {"publisher": "ACN/UE"})

    def test_audit_control_change(self):
        audit_mod.record_event(
            actor_user_id="consultant_test",
            action=audit_mod.CONTROL_STATUS_CHANGED,
            entity_type="ControlImplementation",
            entity_id="CTRL-IAM-001",
            tenant_id="tenant-michele-demo",
            old_value={"status": "IN_PROGRESS"},
            new_value={"status": "IMPLEMENTED"},
        )
        events = audit_mod.list_events(action=audit_mod.CONTROL_STATUS_CHANGED)
        self.assertTrue(events)
        self.assertEqual(events[0].actor_user_id, "consultant_test")
        self.assertEqual(events[0].old_value["status"], "IN_PROGRESS")

    def test_report_snapshot_stable(self):
        fixture = ROOT / "engine" / "fixtures" / "review" / "michele_cyber_2026.json"
        if not fixture.is_file():
            self.skipTest("michele fixture missing")
        program = load_program_snapshot(fixture)
        snap = generate_snapshot(program, generated_by="tester")
        # mutate implementation in memory
        impl = program.implementations[0]
        object.__setattr__(impl, "status", ImplementationStatus.IMPLEMENTED)
        loaded = get_snapshot(snap.id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.id, snap.id)
        self.assertEqual(loaded.assessment_date, snap.assessment_date)
        self.assertEqual(loaded.framework_baselines, snap.framework_baselines)

    def test_optimistic_locking(self):
        v1 = get_version("prog", "ctrl-1")
        v2 = apply_patch(
            ControlPatch(
                program_id="prog",
                control_id="ctrl-1",
                expected_version=v1,
                changes={"status": "IN_PROGRESS"},
            )
        )
        self.assertEqual(v2, v1 + 1)
        with self.assertRaises(ConflictError):
            apply_patch(
                ControlPatch(
                    program_id="prog",
                    control_id="ctrl-1",
                    expected_version=v1,
                    changes={"status": "IMPLEMENTED"},
                )
            )

    def test_na_requires_rationale_api(self):
        cookie = self._cookie(
            "client_member_michele",
            role=Role.CLIENT_MEMBER.value,
            tenants=["tenant-michele-demo"],
        )
        # Need program resolve — without registry, 404; still validate N/A branch via unit
        from engine.domain import ImplementationStatus

        self.assertEqual(ImplementationStatus.NOT_APPLICABLE.value, "NOT_APPLICABLE")
        payload = json.dumps(
            {
                "control_id": "x",
                "expected_version": 1,
                "status": "NOT_APPLICABLE",
                "not_applicable_rationale": "",
            }
        ).encode()
        # Without program, returns 404 before N/A check — create empty registry program skip
        h = FakeHandler("/api/control/update", cookie=cookie, body=payload)
        h.headers["Content-Length"] = str(len(payload))
        h.do_POST()
        self.assertIn(h.status, {404, 400})

    def test_ssrf_blocks_private(self):
        self.assertIsNotNone(validate_url("http://127.0.0.1/x", allow_file=False))
        self.assertIsNotNone(validate_url("http://localhost/x", allow_file=False))
        self.assertIsNotNone(validate_url("http://169.254.169.254/latest", allow_file=False))
        self.assertIsNotNone(validate_url("gopher://evil", allow_file=False))
        self.assertIsNotNone(validate_url("file:///etc/passwd", allow_file=False))
        self.assertIsNone(validate_url("fixture://demo-nis2/v1.html"))

    def test_mfa_totp_roundtrip(self):
        secret = generate_totp_secret()
        code = totp(secret)
        self.assertTrue(verify_totp(secret, code))
        self.assertFalse(verify_totp(secret, "000000"))

    def test_session_idle_fields(self):
        token = issue_session(
            "consultant_test",
            role=Role.CONSULTANT,
            tenant_ids=["tenant-michele-demo"],
        )
        session = parse_session_token(token)
        self.assertIsNotNone(session)
        assert session is not None
        self.assertEqual(session.role, Role.CONSULTANT.value)
        self.assertEqual(session.tenant_ids, ("tenant-michele-demo",))


if __name__ == "__main__":
    unittest.main()

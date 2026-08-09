"""Hardening: session auth and closed public access."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.api import Handler
from engine.auth_session import (
    issue_session,
    parse_session_token,
    session_cookie_header,
    verify_credentials,
)


class AuthSessionTests(unittest.TestCase):
    def test_signed_session_roundtrip(self):
        with mock.patch.dict(
            os.environ,
            {"WAYFOLD_SESSION_SECRET": "test-secret-abc"},
            clear=False,
        ):
            token = issue_session("consultant@wayfold.xyz", is_superuser=True)
            session = parse_session_token(token)
            self.assertIsNotNone(session)
            assert session is not None
            self.assertEqual(session.username, "consultant@wayfold.xyz")
            self.assertTrue(session.is_superuser)
            self.assertIsNone(parse_session_token(token[:-1] + ("0" if token[-1] != "0" else "1")))

    def test_verify_credentials(self):
        with mock.patch.dict(
            os.environ,
            {
                "WAYFOLD_AUTH_USER": "a@b.c",
                "WAYFOLD_AUTH_PASSWORD": "secret",
            },
            clear=False,
        ):
            self.assertTrue(verify_credentials("a@b.c", "secret"))
            self.assertFalse(verify_credentials("a@b.c", "wrong"))

    def test_production_mode_requires_auth(self):
        captured: dict = {}

        class FakeHandler(Handler):
            def __init__(self, path: str, cookie: str | None = None):
                self.path = path
                self.headers = {"Cookie": cookie} if cookie else {}
                self.wfile = mock.Mock()
                self.wfile.write = lambda b: captured.__setitem__("body", b)
                self.rfile = mock.Mock()
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

        env = {
            "WAYFOLD_OPEN_ACCESS": "0",
            "WAYFOLD_ALLOW_QS_AUTH": "0",
            "WAYFOLD_SEED_DEMO": "0",
            "WAYFOLD_SESSION_SECRET": "prod-test-secret",
            "WAYFOLD_AUTH_USER": "c@wayfold.xyz",
            "WAYFOLD_AUTH_PASSWORD": "pw",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            FakeHandler("/portfolio?superuser=1").do_GET()
            self.assertEqual(captured["status"], 302)
            self.assertTrue(captured["headers"]["Location"].startswith("/login"))

            FakeHandler("/api/portfolio?superuser=1").do_GET()
            self.assertEqual(captured["status"], 401)
            self.assertIn("authentication_required", captured["body"].decode())

            token = issue_session("c@wayfold.xyz", is_superuser=True)
            cookie = session_cookie_header(token, secure=False).split(";", 1)[0]
            FakeHandler("/portfolio", cookie=cookie).do_GET()
            self.assertEqual(captured["status"], 200)
            self.assertIn("WayFold Compliance", captured["body"].decode())

            FakeHandler("/login").do_GET()
            self.assertEqual(captured["status"], 200)
            body = captured["body"].decode()
            self.assertIn("Accedi", body)
            self.assertIn('type="text"', body)
            self.assertNotIn('type="email"', body)


if __name__ == "__main__":
    unittest.main()

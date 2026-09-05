from __future__ import annotations

import stat
import tempfile
import unittest
from pathlib import Path

from devharness.dashboard_security import (
    RequestSecurityError,
    issue_csrf_token,
    issue_session_token,
    mask_dashboard_text,
    mask_dashboard_value,
    private_atomic_write,
    require_opaque_identifier,
    validate_request_security,
)


class DashboardSecurityTests(unittest.TestCase):
    def test_private_atomic_write_replaces_existing_file_with_private_modes(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            root = Path(temporary) / "dashboard"
            root.mkdir(mode=0o755)
            target = root / "review.html"
            target.write_text("old", encoding="utf-8")
            target.chmod(0o644)

            private_atomic_write(target, "new")

            self.assertEqual("new", target.read_text(encoding="utf-8"))
            self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))
            self.assertEqual(0o700, stat.S_IMODE(root.stat().st_mode))

    def test_masking_recurses_redacts_secret_keys_and_replaces_private_roots(self) -> None:
        private_root = Path("/Users/example/worktree")

        masked = mask_dashboard_value(
            {
                "command": "/Users/example/worktree/.venv/bin/python -m unittest tests",
                "api_token": "secret",
                "api_key": "secret-key",
                "nested": [{"object_path": "/private/raw/object", "safe": "value"}],
            },
            private_roots=(private_root,),
        )

        self.assertEqual(
            {
                "command": "[private-root]/.venv/bin/python -m unittest tests",
                "api_token": "[redacted]",
                "api_key": "[redacted]",
                "nested": [{"object_path": "[redacted]", "safe": "value"}],
            },
            masked,
        )
        self.assertEqual(
            "open [private-root]/review.html",
            mask_dashboard_text(
                "open /Users/example/worktree/review.html",
                private_roots=(private_root,),
            ),
        )

    def test_opaque_identifiers_reject_path_url_and_whitespace_syntax(self) -> None:
        invalid = (
            "task/child",
            r"task\child",
            "task%2fchild",
            "task%2Fchild",
            "task..child",
            "task\x00child",
            "file:///tmp/task",
            "https:remote-task",
            "task child",
            " task",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_opaque_identifier(value, "task_id")

        self.assertEqual(
            "task:opaque_1-2", require_opaque_identifier("task:opaque_1-2", "task_id")
        )

    def test_tokens_are_high_entropy_and_valid_get_and_post_requests_pass(self) -> None:
        session = issue_session_token()
        other_session = issue_session_token()
        csrf = issue_csrf_token(session)
        origin = "http://127.0.0.1:8765"

        self.assertNotEqual(session, other_session)
        self.assertGreaterEqual(len(session), 40)
        self.assertNotEqual(csrf, issue_csrf_token(other_session))
        validate_request_security(
            host="127.0.0.1:8765",
            token=session,
            expected_token=session,
            method="GET",
            origin=None,
            expected_origin=origin,
            csrf_token=None,
            expected_csrf_token=csrf,
        )
        validate_request_security(
            host="localhost:8765",
            token=session,
            expected_token=session,
            method="POST",
            origin=origin,
            expected_origin=origin,
            csrf_token=csrf,
            expected_csrf_token=csrf,
        )

    def test_request_security_fails_closed_for_host_token_origin_and_csrf(self) -> None:
        valid = {
            "host": "127.0.0.1:8765",
            "token": "session",
            "expected_token": "session",
            "method": "POST",
            "origin": "http://127.0.0.1:8765",
            "expected_origin": "http://127.0.0.1:8765",
            "csrf_token": "csrf",
            "expected_csrf_token": "csrf",
        }
        attacks = (
            {"host": "0.0.0.0"},
            {"token": "wrong"},
            {"token": "", "expected_token": ""},
            {"origin": "http://localhost:8765"},
            {"origin": "", "expected_origin": ""},
            {"csrf_token": "wrong"},
            {"csrf_token": "", "expected_csrf_token": ""},
            {"method": "DELETE"},
        )
        for attack in attacks:
            values = dict(valid)
            values.update(attack)
            with self.subTest(attack=attack), self.assertRaises(RequestSecurityError):
                validate_request_security(**values)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import http.client
import threading
import unittest
from pathlib import Path

from devharness.dashboard_server import (
    DashboardConfig,
    DashboardServices,
    create_dashboard_server,
)
from tests.test_dashboard_render import review_view


TASK = "task:opaque-1"


class DashboardHttpSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.load_count = 0

        def load_view(task_id: str) -> object:
            self.load_count += 1
            view = review_view()
            view.task["task_id"] = task_id
            return view

        self.config = DashboardConfig(
            host="127.0.0.1",
            port=0,
            session_token="one-use-bootstrap-token",
            data_root=Path("/tmp/devharness-dashboard-http-test"),
        )
        self.services = DashboardServices(
            load_view=load_view,
            resolve_evidence=lambda task_id, evidence_id, disclose_raw: (_ for _ in ()).throw(
                AssertionError("unexpected resolver call")
            ),
            validate_feature=lambda task_id, subject_ref, form: object(),
            decide=lambda view, form: (_ for _ in ()).throw(ValueError("Hard Block")),
            export_history=lambda view, sections: b"{}",
        )
        self.server = create_dashboard_server(self.config, self.services)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(
        self,
        method: str,
        target: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> http.client.HTTPResponse:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        request_headers = {"Host": f"127.0.0.1:{self.port}"}
        request_headers.update(headers or {})
        connection.request(method, target, body=body, headers=request_headers)
        response = connection.getresponse()
        response.body = response.read()
        connection.close()
        return response

    def bootstrap(self) -> tuple[str, str]:
        response = self.request(
            "GET", f"/tasks/{TASK}?session_token=one-use-bootstrap-token"
        )
        self.assertEqual(303, response.status)
        self.assertEqual(f"/tasks/{TASK}", response.getheader("Location"))
        cookie = response.getheader("Set-Cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertNotIn("session_token", response.getheader("Location"))
        return cookie.split(";", 1)[0], response.getheader("Location")

    def test_server_refuses_non_loopback_bind(self) -> None:
        with self.assertRaisesRegex(ValueError, "loopback"):
            create_dashboard_server(
                DashboardConfig(
                    host="0.0.0.0",
                    port=0,
                    session_token="token",
                    data_root=Path("/tmp/devharness-dashboard-http-test"),
                ),
                self.services,
            )

    def test_bootstrap_is_one_use_then_clean_cookie_url_is_required(self) -> None:
        cookie, clean_path = self.bootstrap()

        repeated = self.request(
            "GET", f"/tasks/{TASK}?session_token=one-use-bootstrap-token"
        )
        clean = self.request("GET", clean_path, headers={"Cookie": cookie})
        no_token = self.request("GET", clean_path)

        self.assertEqual(403, repeated.status)
        self.assertEqual(200, clean.status)
        self.assertEqual(403, no_token.status)

    def test_bootstrap_rejects_non_loopback_host_without_consuming_token(self) -> None:
        rejected = self.request(
            "GET",
            f"/tasks/{TASK}?session_token=one-use-bootstrap-token",
            headers={"Host": "evil.invalid"},
        )

        self.assertEqual(403, rejected.status)
        cookie, clean_path = self.bootstrap()
        self.assertEqual(
            200, self.request("GET", clean_path, headers={"Cookie": cookie}).status
        )

    def test_missing_token_is_rejected_before_unknown_route_is_disclosed(self) -> None:
        self.assertEqual(403, self.request("GET", "/").status)

    def test_unauthenticated_post_is_rejected_before_its_body_is_parsed(self) -> None:
        response = self.request(
            "POST",
            f"/tasks/{TASK}",
            headers={
                "Origin": f"http://127.0.0.1:{self.port}",
                "Content-Type": "text/plain",
            },
            body=b"not-a-form",
        )

        self.assertEqual(403, response.status)
        self.assertIn(b"session token is invalid", response.body)

    def test_every_response_has_no_store_csp_nosniff_and_no_referrer(self) -> None:
        cookie, clean_path = self.bootstrap()
        responses = (
            self.request("GET", clean_path, headers={"Cookie": cookie}),
            self.request("GET", "/", headers={"Cookie": cookie}),
            self.request("GET", clean_path),
        )
        for response in responses:
            with self.subTest(status=response.status):
                self.assertEqual("no-store", response.getheader("Cache-Control"))
                self.assertEqual("nosniff", response.getheader("X-Content-Type-Options"))
                self.assertEqual("no-referrer", response.getheader("Referrer-Policy"))
                csp = response.getheader("Content-Security-Policy")
                self.assertIn("default-src 'none'", csp)
                self.assertIn("style-src 'nonce-", csp)
                self.assertIn("script-src 'nonce-", csp)
                self.assertIn("img-src 'self' data:", csp)
                self.assertIn("form-action 'self'", csp)
                self.assertIn("frame-ancestors 'none'", csp)

    def test_post_requires_exact_origin_and_csrf_and_maps_hard_block_to_conflict(self) -> None:
        cookie, clean_path = self.bootstrap()
        origin = f"http://127.0.0.1:{self.port}"
        valid = {
            "Cookie": cookie,
            "Origin": origin,
            "X-CSRF-Token": self.config.csrf_token,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        attacks = (
            {**valid, "Origin": "http://evil.invalid"},
            {**valid, "X-CSRF-Token": "wrong"},
        )
        for headers in attacks:
            with self.subTest(headers=headers):
                self.assertEqual(
                    403,
                    self.request("POST", clean_path, headers=headers, body=b"decision=accept").status,
                )

        self.assertEqual(
            409,
            self.request("POST", clean_path, headers=valid, body=b"decision=accept").status,
        )

    def test_request_logging_is_disabled(self) -> None:
        self.assertFalse(hasattr(self.server.RequestHandlerClass, "log_request_enabled"))
        self.assertEqual(
            None,
            self.server.RequestHandlerClass.log_message(
                object(), "%s", "must not be emitted"
            ),
        )


if __name__ == "__main__":
    unittest.main()

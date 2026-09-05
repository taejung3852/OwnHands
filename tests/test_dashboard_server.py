from __future__ import annotations

import contextlib
import http.cookiejar
import io
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from devharness.dashboard_server import (
    DashboardConfig,
    DashboardResponse,
    DashboardServices,
    create_dashboard_server,
    route_request,
    serve_dashboard,
)
from devharness.dashboard_sources import EvidenceView
from devharness.__main__ import main
from devharness.catalog import Catalog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths


TASK = "task:opaque-1"
SUBJECT = "subject:hwpx:bold"
EVIDENCE = "evidence:direct:1"


@dataclass
class View:
    task: dict
    decision: dict


class ServiceRecorder:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.current_view = View(
            task={"task_id": TASK},
            decision={"submission_allowed": True, "gate": "soft_block"},
        )

    def load_view(self, task_id: str) -> View:
        self.calls.append(("load_view", task_id))
        return self.current_view

    def resolve_evidence(
        self, task_id: str, evidence_id: str, disclose_raw: bool
    ) -> tuple[EvidenceView, bytes | None]:
        self.calls.append(("resolve_evidence", task_id, evidence_id, disclose_raw))
        return (
            EvidenceView(
                evidence_id=evidence_id,
                reference_kind="store",
                task_id=task_id,
                result="pass",
                basis="observed",
                content_hash="a" * 64,
                content_size=25,
                redaction_status="redacted",
                raw_available=True,
                metadata={"subject_ref": SUBJECT},
            ),
            b"<script>alert(1)</script>" if disclose_raw else None,
        )

    def validate_feature(self, task_id: str, subject_ref: str, form: dict[str, str]) -> object:
        self.calls.append(("validate_feature", task_id, subject_ref, form))
        return object()

    def decide(self, view: View, form: dict[str, str]) -> object:
        self.calls.append(("decide", view, form))
        return object()

    def export_history(self, view: View, sections: tuple[str, ...]) -> bytes:
        self.calls.append(("export_history", view, sections))
        return b'{"history":[]}'


class DashboardRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.recorder = ServiceRecorder()
        self.services = DashboardServices(
            load_view=self.recorder.load_view,
            resolve_evidence=self.recorder.resolve_evidence,
            validate_feature=self.recorder.validate_feature,
            decide=self.recorder.decide,
            export_history=self.recorder.export_history,
        )
        self.config = DashboardConfig(
            host="127.0.0.1",
            port=8765,
            session_token="session-token",
            data_root=Path("/tmp/devharness-dashboard-test"),
        )
        self.headers = {
            "Host": "127.0.0.1:8765",
            "Cookie": "devharness_session=session-token",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, tuple[str, ...]] | None = None,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> DashboardResponse:
        return route_request(
            method=method,
            path=path,
            query=query or {},
            headers=headers or self.headers,
            body=body,
            config=self.config,
            services=self.services,
        )

    def test_exactly_five_get_route_shapes_are_public(self) -> None:
        paths = (
            f"/tasks/{TASK}",
            f"/tasks/{TASK}/harness",
            f"/tasks/{TASK}/validate/{SUBJECT}",
            f"/tasks/{TASK}/history",
            f"/tasks/{TASK}/evidence/{EVIDENCE}",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(200, self.request("GET", path).status)
        self.assertEqual(404, self.request("GET", "/").status)
        self.assertEqual(404, self.request("GET", f"/tasks/{TASK}/analytics").status)

    def test_unsafe_encoded_or_traversal_identifiers_fail_before_lookup(self) -> None:
        attacks = (
            "/tasks/task%2Fchild",
            "/tasks/task%252Fchild",
            "/tasks/task..child",
            f"/tasks/{TASK}/evidence/evidence%2Fchild",
        )
        for path in attacks:
            self.recorder.calls.clear()
            with self.subTest(path=path):
                self.assertEqual(400, self.request("GET", path).status)
                self.assertEqual([], self.recorder.calls)

    def test_evidence_is_metadata_by_default_and_raw_requires_explicit_one(self) -> None:
        path = f"/tasks/{TASK}/evidence/{EVIDENCE}"

        metadata = self.request("GET", path)
        raw = self.request("GET", path, query={"raw": ("1",)})

        self.assertEqual(
            ("resolve_evidence", TASK, EVIDENCE, False), self.recorder.calls[1]
        )
        self.assertEqual(
            ("resolve_evidence", TASK, EVIDENCE, True), self.recorder.calls[3]
        )
        self.assertNotIn(b"<script>", metadata.body)
        self.assertNotIn(b"<script>alert(1)</script>", raw.body)
        self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", raw.body)

    def test_task_post_reloads_current_view_before_decision(self) -> None:
        headers = {
            **self.headers,
            "Origin": "http://127.0.0.1:8765",
            "X-CSRF-Token": self.config.csrf_token,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = self.request(
            "POST",
            f"/tasks/{TASK}",
            headers=headers,
            body=b"decision=revise",
        )

        self.assertEqual(303, response.status)
        self.assertEqual("load_view", self.recorder.calls[0][0])
        self.assertEqual("decide", self.recorder.calls[1][0])
        self.assertIs(self.recorder.current_view, self.recorder.calls[1][1])

    def test_validation_post_uses_the_same_validation_route(self) -> None:
        headers = {
            **self.headers,
            "Origin": "http://127.0.0.1:8765",
            "X-CSRF-Token": self.config.csrf_token,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        path = f"/tasks/{TASK}/validate/{SUBJECT}"

        response = self.request(
            "POST", path, headers=headers, body=b"input_summary=sample.hwpx"
        )

        self.assertEqual(303, response.status)
        self.assertEqual(path, dict(response.headers)["Location"])
        self.assertEqual(
            ("validate_feature", TASK, SUBJECT, {"input_summary": "sample.hwpx"}),
            self.recorder.calls[0],
        )

    def test_dashboard_cli_builds_private_local_services_without_printing_data_root(self) -> None:
        captured: list[tuple[DashboardConfig, DashboardServices]] = []
        arguments = [
            "devharness",
            "dashboard",
            "--data-root",
            "/tmp/private-dashboard-data",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
        ]

        with patch("sys.argv", arguments), patch(
            "devharness.__main__.serve_dashboard",
            side_effect=lambda config, services: captured.append((config, services)),
        ), patch("builtins.print") as output:
            self.assertEqual(0, main())

        self.assertEqual(1, len(captured))
        config, services = captured[0]
        self.assertEqual("127.0.0.1", config.host)
        self.assertEqual(0, config.port)
        self.assertEqual(Path("/tmp/private-dashboard-data"), config.data_root)
        self.assertGreaterEqual(len(config.session_token), 40)
        self.assertIsInstance(services, DashboardServices)
        self.assertFalse(output.called)

    def test_dashboard_cli_rejects_non_loopback_before_starting_server(self) -> None:
        arguments = [
            "devharness",
            "dashboard",
            "--data-root",
            "/tmp/private-dashboard-data",
            "--host",
            "0.0.0.0",
            "--port",
            "8765",
        ]
        with patch("sys.argv", arguments), patch(
            "devharness.__main__.serve_dashboard"
        ) as serve, self.assertRaises(SystemExit):
            main()
        serve.assert_not_called()

    def test_serve_dashboard_prints_and_follows_a_real_task_bootstrap_url(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            data_root = Path(temporary) / "data"
            catalog = Catalog.open(DataPaths.resolve(data_root))
            registry = IdentityRegistry(catalog)
            project = registry.register_project("file:///bootstrap-repo")
            worktree = registry.register_worktree(
                project.project_id, "file:///bootstrap-repo/main"
            )
            registry.create_task(
                worktree.worktree_id,
                mode="managed",
                commit="older123",
                branch="older",
                cwd="/bootstrap-repo/main",
                environment_ref="local-test",
            )
            task = registry.create_task(
                worktree.worktree_id,
                mode="managed",
                commit="bootstrap123",
                branch="main",
                cwd="/bootstrap-repo/main",
                environment_ref="local-test",
            )
            catalog.close()

            def load_view(task_id: str) -> View:
                if task_id != task.task_id:
                    raise ValueError(f"unknown task: {task_id}")
                return View(task={"task_id": task_id}, decision={})

            services = DashboardServices(
                load_view=load_view,
                resolve_evidence=lambda *_args: (_ for _ in ()).throw(
                    AssertionError("unexpected resolver call")
                ),
                validate_feature=lambda *_args: object(),
                decide=lambda *_args: object(),
                export_history=lambda *_args: b"{}",
            )
            config = DashboardConfig(
                host="127.0.0.1",
                port=0,
                session_token="followable-one-use-token",
                data_root=data_root,
            )
            output = io.StringIO()
            servers = []
            real_create = create_dashboard_server

            def capture_server(config: DashboardConfig, services: DashboardServices):
                server = real_create(config, services)
                servers.append(server)
                return server

            def run() -> None:
                with contextlib.redirect_stdout(output):
                    serve_dashboard(config, services)

            with patch(
                "devharness.dashboard_server.create_dashboard_server",
                side_effect=capture_server,
            ):
                thread = threading.Thread(target=run, daemon=True)
                thread.start()
                deadline = time.monotonic() + 2
                while (not servers or "dashboard=" not in output.getvalue()) and time.monotonic() < deadline:
                    time.sleep(0.01)
                try:
                    printed = output.getvalue().strip()
                    self.assertTrue(printed.startswith("dashboard=http://"), printed)
                    url = printed.removeprefix("dashboard=")
                    self.assertNotIn("{task_id}", url)
                    self.assertIn(f"/tasks/{task.task_id}?session_token=", url)
                    opener = urllib.request.build_opener(
                        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
                    )
                    with opener.open(url, timeout=2) as response:
                        self.assertEqual(200, response.status)
                        self.assertEqual(
                            f"/tasks/{task.task_id}",
                            urllib.parse.urlsplit(response.url).path,
                        )
                        self.assertNotIn("session_token", response.url)
                finally:
                    if servers:
                        servers[0].shutdown()
                    thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()

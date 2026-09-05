from __future__ import annotations

import re
import stat
import tempfile
import unittest
from pathlib import Path

from devharness.dashboard_render import (
    render_document,
    render_evidence_detail,
    render_feature_validation,
    render_harness_status,
    render_history,
    render_task_review,
)
from devharness.dashboard_server import (
    DashboardConfig,
    DashboardServices,
    route_request,
)
from devharness.dashboard_sources import EvidenceView
from devharness.dashboard_view import TaskReviewView


TASK = "task:review-1"
EVIDENCE = "evidence:diagram-1"


def review_view(*, gate: str = "soft_block") -> TaskReviewView:
    decisions = (
        ("revise", "reject", "additional_validation")
        if gate == "hard_block"
        else ("accept", "revise", "reject", "additional_validation", "risk_acceptance")
    )
    return TaskReviewView(
        task={
            "project_id": "project:1",
            "worktree_id": "worktree:1",
            "task_id": TASK,
            "mode": "managed",
            "commit": "abc123",
            "branch": "main<script>alert(1)</script>",
            "environment_ref": "local-test",
            "created_at": "2026-09-06T12:00:00+00:00",
        },
        summary={
            "disclosure_order": ("summary", "trace", "evidence", "decision"),
            "goal": "Bold <script>alert(1)</script> text",
            "change_statement": "Keep <strong>markup</strong> inert",
            "changed_paths": ("src/widget.py",),
            "declared_relations": ("relation:widget",),
            "gate": gate,
            "warnings": ("Human review is <unknown>",),
            "contract": {"status": "closed", "contract_id": "contract:1"},
        },
        freshness={
            "state": "fresh",
            "event_head": 8,
            "projected_sequence": 8,
            "lag": 0,
            "projection_state": "ready",
            "last_error": None,
            "projection_updated_at": "2026-09-06T12:00:00+00:00",
        },
        completeness={
            "state": "unobserved",
            "missing": ("human_feature_observation",),
            "source_status": {"m3": "closed", "m4": "closed"},
        },
        diagram={
            "state": "observed",
            "kind": "dependency_impact",
            "nodes": (
                {"node_id": "changed:src/widget.py", "kind": "changed_path", "source_ref": "relation:widget"},
                {"node_id": "test:widget", "kind": "declared_target", "source_ref": "relation:widget"},
            ),
            "edges": (
                {
                    "from": "changed:src/widget.py",
                    "to": "test:widget",
                    "relation_type": "test",
                    "source_ref": "relation:widget",
                    "evidence_refs": (EVIDENCE,),
                },
            ),
            "evidence_refs": (EVIDENCE,),
        },
        relations=(
            {
                "relation_id": "relation:widget",
                "relation_type": "test",
                "target_ref": "test:widget",
                "changed_paths": ("src/widget.py",),
                "basis": "observed",
                "evidence_refs": (EVIDENCE,),
                "priority": "required",
            },
        ),
        verification=(
            {
                "kind": "test",
                "test_id": "test:widget",
                "subject_ref": "subject:widget",
                "result": "passed",
                "source_result": "pass",
                "basis": "observed",
                "evidence_refs": (EVIDENCE,),
            },
            {
                "kind": "direct_feature_validation",
                "subject_ref": "subject:hwpx:bold",
                "result": "unknown",
                "source_result": "not_run",
                "basis": "unobserved",
                "evidence_refs": (),
            },
        ),
        guarantees=(
            {
                "claim_id": "task_guarantees",
                "status": "not_evaluated",
                "verdict": None,
                "basis": "unobserved",
                "evidence_refs": (),
            },
        ),
        harness={
            "baseline": {"status": "observed", "baseline_id": "baseline:1"},
            "context_status": {"status": "observed", "manifest_ref": "manifest:1"},
            "source": {
                "scope": "project",
                "status": "closed",
                "task_applicable": False,
                "observed_at": "2026-09-06T12:00:00+00:00",
                "fingerprint": "sha256:" + "a" * 64,
                "reasons": ("Project evidence only",),
            },
            "project_controls": None,
            "controls": {
                name: {
                    stage: {
                        "result": "not_run",
                        "basis": "unobserved",
                        "evidence_refs": (),
                        "reason": "Task closure missing",
                    }
                    for stage in ("configured", "loaded", "enforced")
                }
                for name in ("config", "agents", "rules", "hooks", "sandbox", "approval")
            },
            "imported_controls": None,
        },
        assurance={
            "source": {
                "status": "closed",
                "task_applicable": True,
                "fingerprint": "sha256:" + "d" * 64,
            },
            "packet_id": "packet:1",
            "contract_fingerprint": "sha256:" + "b" * 64,
            "gate": {
                "decision": gate,
                "basis": "observed",
                "fingerprint": "sha256:" + "c" * 64,
                "hard_reasons": ("Required test failed",) if gate == "hard_block" else (),
                "soft_reasons": ("Human observation missing",) if gate == "soft_block" else (),
                "evidence_refs": (EVIDENCE,),
            },
        },
        decision={
            "submission_allowed": True,
            "allowed_decisions": decisions,
            "gate": gate,
            "reason": None,
            "current": None,
        },
        history=(
            {
                "sequence": 1,
                "event_id": "event:1",
                "event_type": "task.created",
                "occurred_at": "2026-09-06T12:00:00+00:00",
                "redaction_status": "not_needed",
                "references": {},
            },
        ),
        evidence=(
            EvidenceView(
                evidence_id=EVIDENCE,
                reference_kind="store",
                task_id=TASK,
                result="pass",
                basis="observed",
                content_hash="a" * 64,
                content_size=24,
                redaction_status="redacted",
                raw_available=True,
                metadata={"subject_ref": "subject:widget"},
            ),
        ),
        assembled_at="2026-09-06T12:00:00+00:00",
    )


class DashboardRenderTests(unittest.TestCase):
    def test_task_review_orders_progressive_sections_and_escapes_all_dynamic_text(self) -> None:
        page = render_task_review(review_view(), csrf_token='csrf"><script>alert(2)</script>')

        positions = [page.index(f'id="{section}"') for section in ("summary", "trace", "evidence", "decision")]
        self.assertEqual(sorted(positions), positions)
        self.assertIn("<details", page)
        self.assertIn("<summary", page)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertNotIn("<script>alert(2)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn('name="csrf_token"', page)

    def test_bounded_diagram_has_unique_label_ids_and_duplicate_html_evidence_paths(self) -> None:
        page = render_task_review(review_view(), csrf_token="csrf")

        self.assertRegex(
            page,
            r'<svg[^>]+aria-labelledby="task-[^"]+-diagram-title task-[^"]+-diagram-desc"',
        )
        self.assertRegex(page, r'<svg[^>]*>\s*<title id="task-[^"]+-diagram-title">')
        self.assertIn('class="diagram-fallback"', page)
        self.assertGreaterEqual(page.count(f"/evidence/{EVIDENCE}"), 2)
        ids = re.findall(r'\bid="(task-[^"]+)"', page)
        self.assertEqual(len(ids), len(set(ids)))

    def test_relation_checklist_does_not_emit_a_broken_validation_route_for_non_subject_refs(self) -> None:
        page = render_task_review(review_view(), csrf_token="csrf")

        self.assertNotIn("/validate/test:widget", page)
        self.assertIn("직접 검증 대상 아님", page)

    def test_hard_block_omits_acceptance_controls_but_keeps_safe_decisions(self) -> None:
        page = render_task_review(review_view(gate="hard_block"), csrf_token="csrf")

        self.assertNotIn('value="accept"', page)
        self.assertNotIn('value="risk_acceptance"', page)
        self.assertIn('value="revise"', page)
        self.assertIn("Hard Block", page)

    def test_decision_form_submits_current_identity_and_assurance_references_for_server_recheck(self) -> None:
        page = render_task_review(review_view(), csrf_token="csrf")

        expected = {
            "task_id": TASK,
            "assurance_packet_fingerprint": "sha256:" + "d" * 64,
            "gate_fingerprint": "sha256:" + "c" * 64,
            "gate_decision": "soft_block",
            "evidence_refs": EVIDENCE,
        }
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertIn(f'name="{name}" value="{value}"', page)

    def test_all_route_fragments_render_source_values_without_active_markup(self) -> None:
        view = review_view()
        evidence = view.evidence[0]
        fragments = (
            render_harness_status(view),
            render_feature_validation(view, subject_ref='subject:hwpx:<script>', csrf_token="csrf"),
            render_history(view),
            render_evidence_detail(view, evidence=evidence, raw=b"<script>alert(9)</script>"),
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment[:40]):
                self.assertNotIn("<script>alert", fragment)
        self.assertIn("&lt;script&gt;alert(9)&lt;/script&gt;", fragments[-1])
        self.assertIn("<pre", fragments[-1])

    def test_document_has_korean_landmarks_one_h1_and_nonce_bound_local_assets(self) -> None:
        document = render_document(
            title='Review <unsafe>',
            task_id=TASK,
            main=render_task_review(review_view(), csrf_token="csrf"),
            status="Freshness updated without focus movement",
            nonce='nonce"><bad>',
        ).decode("utf-8")

        self.assertIn('<html lang="ko"', document)
        self.assertIn('class="skip-link" href="#main-content"', document)
        for landmark in ("<header", "<nav", '<main id="main-content"', "<footer"):
            self.assertIn(landmark, document)
        self.assertEqual(1, len(re.findall(r"<h1(?:\s|>)", document)))
        self.assertNotIn("<bad>", document)
        self.assertIn('role="status"', document)
        self.assertIn("<style nonce=", document)
        self.assertIn("<script nonce=", document)


class DashboardRendererIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.view = review_view()
        self.decision_forms: list[dict[str, str]] = []
        self.validation_forms: list[dict[str, str]] = []
        self.config = DashboardConfig(
            host="127.0.0.1",
            port=8765,
            session_token="session-token",
            data_root=Path("/tmp/dashboard-render-integration"),
        )
        self.services = DashboardServices(
            load_view=lambda task_id: self.view,
            resolve_evidence=lambda task_id, evidence_id, disclose_raw: (
                self.view.evidence[0],
                b"<script>alert(9)</script>" if disclose_raw else None,
            ),
            validate_feature=lambda task_id, subject_ref, form: self.validation_forms.append(form),
            decide=lambda view, form: self.decision_forms.append(form),
            export_history=lambda view, sections: b'{"history":[]}',
        )
        self.headers = {
            "Host": "127.0.0.1:8765",
            "Cookie": "devharness_session=session-token",
        }

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        query: dict[str, tuple[str, ...]] | None = None,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ):
        return route_request(
            method=method,
            path=path,
            query=query or {},
            headers=headers or self.headers,
            body=body,
            config=self.config,
            services=self.services,
        )

    def test_all_five_routes_use_their_renderer_inside_the_accessible_document(self) -> None:
        routes = (
            (f"/tasks/{TASK}", "summary"),
            (f"/tasks/{TASK}/harness", "harness-page"),
            (f"/tasks/{TASK}/validate/subject:hwpx:bold", "validation-page"),
            (f"/tasks/{TASK}/history", "history-page"),
            (f"/tasks/{TASK}/evidence/{EVIDENCE}", "evidence-detail"),
        )
        for path, marker in routes:
            with self.subTest(path=path):
                response = self.request(path)
                document = response.body.decode("utf-8")
                self.assertEqual(200, response.status)
                self.assertIn('<html lang="ko"', document)
                self.assertIn(f'id="{marker}"', document)
                self.assertEqual(1, len(re.findall(r"<h1(?:\s|>)", document)))
                csp = dict(response.headers)["Content-Security-Policy"]
                nonce = re.search(r'<style nonce="([^"]+)"', document).group(1)
                self.assertIn(f"style-src 'nonce-{nonce}'", csp)
                self.assertIn(f"script-src 'nonce-{nonce}'", csp)

    def test_native_hidden_csrf_forms_submit_without_javascript_or_leaking_token_to_services(self) -> None:
        headers = {
            **self.headers,
            "Origin": "http://127.0.0.1:8765",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        response = self.request(
            f"/tasks/{TASK}",
            method="POST",
            headers=headers,
            body=f"csrf_token={self.config.csrf_token}&decision=revise".encode(),
        )

        self.assertEqual(303, response.status)
        self.assertEqual([{"decision": "revise"}], self.decision_forms)

    def test_history_export_is_an_attachment_without_any_local_path_header(self) -> None:
        response = self.request(
            f"/tasks/{TASK}/history",
            query={"format": ("json",), "section": ("summary", "history")},
        )

        self.assertEqual(200, response.status)
        headers = dict(response.headers)
        self.assertEqual("attachment; filename=devharness-history.json", headers["Content-Disposition"])
        self.assertNotIn(str(self.config.data_root), str(response.headers))

    def test_explicit_saved_export_is_private_and_never_exposes_its_local_path(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            self.config = DashboardConfig(
                host="127.0.0.1",
                port=8765,
                session_token="session-token",
                data_root=Path(temporary) / "data",
            )
            response = self.request(
                f"/tasks/{TASK}/history",
                query={"format": ("json",), "section": ("history",), "save": ("1",)},
            )
            exports = list((self.config.data_root / "exports").glob("*.json"))

            self.assertEqual(200, response.status)
            self.assertEqual(1, len(exports))
            self.assertEqual(0o600, stat.S_IMODE(exports[0].stat().st_mode))
            self.assertEqual(0o700, stat.S_IMODE(exports[0].parent.stat().st_mode))
            self.assertNotIn(str(exports[0]), response.body.decode("utf-8"))
            self.assertNotIn(str(exports[0]), str(response.headers))


if __name__ == "__main__":
    unittest.main()

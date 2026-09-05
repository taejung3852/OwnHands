from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from devharness.catalog import Catalog
from devharness.dashboard_actions import (
    ValidationObservation,
    ValidationRequest,
    run_feature_validation,
    submit_task_decision,
)
from devharness.dashboard_events import record_assurance_reference
from devharness.dashboard_view import TaskReviewView, _direct_evidence
from devharness.evidence import EvidenceStore
from devharness.events import EventDraft, EventLog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths
from devharness.projections import ProjectionEngine


NOW = "2026-09-06T12:00:00+00:00"
PACKET = "sha256:" + "a" * 64
GATE = "sha256:" + "b" * 64


class HwpxAdapter:
    adapter_ref = "adapter:hwpx:fixture"

    def __init__(self, observation: ValidationObservation) -> None:
        self.observation = observation

    def validate(self, request: ValidationRequest) -> ValidationObservation:
        self.request = request
        return self.observation


class DashboardActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory(dir="/tmp")
        self.catalog = Catalog.open(
            DataPaths.resolve(Path(self.temporary_directory.name) / "data")
        )
        registry = IdentityRegistry(self.catalog)
        project = registry.register_project("file:///repo")
        worktree = registry.register_worktree(project.project_id, "file:///repo/main")
        self.task = registry.create_task(
            worktree.worktree_id,
            mode="managed",
            commit="abc123",
            branch="main",
            cwd="/repo/main",
            environment_ref="macos-arm64-python-3.12",
        )
        self.events = EventLog(self.catalog)
        self.projections = ProjectionEngine(self.catalog, self.events)
        self.events.append(
            EventDraft(
                event_id="event:task:1",
                task_id=self.task.task_id,
                event_type="task.created",
                event_version=1,
                occurred_at=NOW,
                payload={"mode": "managed"},
                collection_method="dashboard-action-test",
                redaction_status="not_needed",
            ),
            lambda payload: payload,
        )
        self.store = EvidenceStore(self.catalog, self.events)

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def request(self) -> ValidationRequest:
        return ValidationRequest(
            self.task.task_id,
            "subject:hwpx:bold",
            "Bold is preserved",
            "sample.hwpx",
        )

    def view(self, *, freshness: str = "fresh", gate: str = "soft_block") -> TaskReviewView:
        allowed = (
            "accept",
            "revise",
            "reject",
            "additional_validation",
            "risk_acceptance",
        )
        if gate == "hard_block":
            allowed = ("revise", "reject", "additional_validation")
        return TaskReviewView(
            task={"task_id": self.task.task_id},
            summary={},
            freshness={
                "state": freshness,
                "projection_state": "ready",
                "event_head": 2,
                "projected_sequence": 2,
            },
            completeness={},
            diagram={},
            relations=(),
            verification=(),
            guarantees=(),
            harness={},
            assurance={
                "source": {
                    "status": "closed",
                    "fingerprint": PACKET,
                    "task_applicable": True,
                },
                "gate": {"decision": gate, "fingerprint": GATE},
            },
            decision={
                "submission_allowed": freshness == "fresh",
                "allowed_decisions": allowed if freshness == "fresh" else (),
                "gate": gate,
            },
            history=(),
            evidence=(),
            assembled_at=NOW,
        )

    def decision_form(self, decision: str = "revise", **changes: str) -> dict[str, str]:
        values = {
            "task_id": self.task.task_id,
            "assurance_packet_fingerprint": PACKET,
            "gate_fingerprint": GATE,
            "gate_decision": "soft_block",
            "decision": decision,
            "decision_source": "product_authority",
            "actor_ref": "actor:local-user",
            "reason": "Human observation is still required",
            "residual_risks": "HWPX rendering remains unobserved",
            "follow_up": "Run the registered HWPX adapter",
            "evidence_refs": "evidence:gate",
        }
        values.update(changes)
        return values

    def record_assurance(self, gate: str = "soft_block") -> None:
        record_assurance_reference(
            self.events,
            event_id="event:assurance:1",
            task_id=self.task.task_id,
            packet_fingerprint=PACKET,
            gate_fingerprint=GATE,
            gate_decision=gate,
            evidence_refs=("evidence:gate",),
            occurred_at=NOW,
        )
        self.projections.project(self.task.task_id)

    def test_missing_adapter_records_unobserved_probe_without_fake_human_observation(self) -> None:
        record = run_feature_validation(
            adapter=None,
            request=self.request(),
            evidence_store=self.store,
            evidence_id="evidence:direct:1",
            occurred_at=NOW,
        )

        self.assertEqual(
            ("direct_feature_probe", "not_run", "unobserved"),
            (record.evidence_type, record.result, record.basis),
        )
        self.assertEqual("M5-06", record.requirement_id)
        self.assertIsNone(record.fields["human_observation"])
        self.assertIsNone(record.fields["generated_output"])
        self.assertIsNone(record.fields["tool_error"])

    def test_hwpx_adapter_records_exact_observation_and_canonical_task_environment(self) -> None:
        observation = ValidationObservation(
            result="pass",
            basis="observed",
            actual="Bold remained present after save and reopen",
            generated_files=("rendered-page-1.png",),
            generated_output="rendered-page-1.png",
            tool_error=None,
            human_observation="Reviewer confirmed the bold run visually",
        )
        adapter = HwpxAdapter(observation)

        record = run_feature_validation(
            adapter=adapter,
            request=self.request(),
            evidence_store=self.store,
            evidence_id="evidence:direct:2",
            occurred_at=NOW,
        )

        self.assertEqual(self.request(), adapter.request)
        self.assertEqual(
            {
                "adapter_ref": "adapter:hwpx:fixture",
                "input": "sample.hwpx",
                "expected": "Bold is preserved",
                "actual": "Bold remained present after save and reopen",
                "environment": "macos-arm64-python-3.12",
                "generated_files": ["rendered-page-1.png"],
                "generated_output": "rendered-page-1.png",
                "tool_error": None,
                "human_observation": "Reviewer confirmed the bold run visually",
                "occurred_at": NOW,
                "task_ref": self.task.task_id,
                "target_commit": "abc123",
            },
            record.fields,
        )
        self.assertEqual("dashboard-feature-adapter:adapter:hwpx:fixture", record.collection_method)
        self.assertEqual(record.fields, __import__("json").loads(self.store.read_content(record.evidence_id)))
        self.assertEqual(record, _direct_evidence(self.store, [record], self.task))

    def test_non_hwpx_adapter_cannot_create_hwpx_evidence(self) -> None:
        adapter = HwpxAdapter(
            ValidationObservation(
                result="pass",
                basis="observed",
                actual="Observed",
                generated_files=(),
                generated_output="output",
                tool_error=None,
                human_observation="Observed by reviewer",
            )
        )
        adapter.adapter_ref = "adapter:generic:fixture"

        with self.assertRaisesRegex(ValueError, "HWPX adapter"):
            run_feature_validation(
                adapter=adapter,
                request=self.request(),
                evidence_store=self.store,
                evidence_id="evidence:direct:3",
                occurred_at=NOW,
            )

    def test_hwpx_adapter_without_human_observation_cannot_store_observed_pass(self) -> None:
        adapter = HwpxAdapter(
            ValidationObservation(
                result="pass",
                basis="observed",
                actual="Automated HWPX output completed",
                generated_files=(),
                generated_output="rendered-page-1.png",
                tool_error=None,
                human_observation=None,
            )
        )

        record = run_feature_validation(
            adapter=adapter,
            request=self.request(),
            evidence_store=self.store,
            evidence_id="evidence:direct:no-human",
            occurred_at=NOW,
        )

        self.assertEqual(("not_run", "unobserved"), (record.result, record.basis))
        self.assertIsNone(record.fields["human_observation"])
        self.assertEqual("rendered-page-1.png", record.fields["generated_output"])

    def test_stale_and_hard_block_decisions_are_rejected_before_append(self) -> None:
        for view, decision in (
            (self.view(freshness="stale"), "revise"),
            (self.view(gate="hard_block"), "accept"),
        ):
            with self.subTest(decision=decision), self.assertRaisesRegex(
                ValueError, "stale|Hard Block"
            ):
                submit_task_decision(
                    view=view,
                    events=self.events,
                    form=self.decision_form(
                        decision,
                        gate_decision=view.assurance["gate"]["decision"],
                    ),
                    event_id="event:decision:rejected",
                    occurred_at=NOW,
                )
        self.assertEqual(1, self.events.head_sequence(self.task.task_id))

    def test_soft_block_risk_acceptance_appends_only_result_decision_fields(self) -> None:
        self.record_assurance()

        record = submit_task_decision(
            view=self.view(),
            events=self.events,
            form=self.decision_form("risk_acceptance"),
            event_id="event:decision:1",
            occurred_at=NOW,
        )

        self.assertEqual("task.decision.recorded", record.event_type)
        self.assertEqual("risk_acceptance", record.payload["decision"])
        self.assertEqual(["HWPX rendering remains unobserved"], record.payload["residual_risks"])
        self.assertTrue(
            {"merge", "deploy", "tool_approval", "action_approval"}.isdisjoint(record.payload)
        )

    def test_risk_acceptance_requires_exact_authority_reason_and_residual_risk(self) -> None:
        self.record_assurance()
        attacks = (
            {"decision_source": "reviewer"},
            {"reason": ""},
            {"residual_risks": ""},
            {"gate_fingerprint": "sha256:" + "c" * 64},
        )
        for attack in attacks:
            with self.subTest(attack=attack), self.assertRaises(ValueError):
                submit_task_decision(
                    view=self.view(),
                    events=self.events,
                    form=self.decision_form("risk_acceptance", **attack),
                    event_id="event:decision:bad",
                    occurred_at=NOW,
                )

    def test_decision_rejects_forged_freshness_or_assurance_closure(self) -> None:
        self.record_assurance()
        base = self.view()
        stale_sequence = replace(
            base,
            freshness={
                **base.freshness,
                "event_head": 3,
                "projected_sequence": 2,
            },
        )
        unclosed_source = replace(
            base,
            assurance={
                **base.assurance,
                "source": {
                    **base.assurance["source"],
                    "status": "mismatch",
                    "task_applicable": False,
                },
            },
        )

        for view in (stale_sequence, unclosed_source):
            with self.subTest(view=view), self.assertRaisesRegex(
                ValueError, "stale|applicable|closed"
            ):
                submit_task_decision(
                    view=view,
                    events=self.events,
                    form=self.decision_form(),
                    event_id="event:decision:forged",
                    occurred_at=NOW,
                )

    def test_decision_rechecks_current_event_head_inside_append_boundary(self) -> None:
        self.record_assurance()
        fresh_view = self.view()
        run_feature_validation(
            adapter=None,
            request=self.request(),
            evidence_store=self.store,
            evidence_id="evidence:direct:after-view",
            occurred_at=NOW,
        )

        with self.assertRaisesRegex(ValueError, "stale"):
            submit_task_decision(
                view=fresh_view,
                events=self.events,
                form=self.decision_form(),
                event_id="event:decision:toctou",
                occurred_at=NOW,
            )

        self.assertEqual(3, self.events.head_sequence(self.task.task_id))


if __name__ == "__main__":
    unittest.main()

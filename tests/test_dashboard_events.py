from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from devharness.catalog import Catalog
from devharness.dashboard_events import (
    record_assurance_reference,
    record_task_decision,
)
from devharness.events import EventConflict, EventDraft, EventLog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths
from devharness.projections import ProjectionEngine


NOW = "2026-09-06T12:00:00+00:00"
PACKET_A = "sha256:" + "a" * 64
PACKET_B = "sha256:" + "b" * 64
GATE_A = "sha256:" + "c" * 64
GATE_B = "sha256:" + "d" * 64


class DashboardEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        paths = DataPaths.resolve(Path(self.temporary_directory.name) / "data")
        self.catalog = Catalog.open(paths)
        registry = IdentityRegistry(self.catalog)
        project = registry.register_project("file:///repo")
        worktree = registry.register_worktree(project.project_id, "file:///repo/main")
        self.task = registry.create_task(
            worktree.worktree_id,
            mode="managed",
            commit="abc123",
            branch="main",
            cwd="/repo/main",
            environment_ref="local-test",
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
                collection_method="dashboard-event-test",
                redaction_status="not_needed",
            ),
            lambda payload: payload,
        )

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def assurance_values(self, **changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "event_id": "event:assurance:1",
            "task_id": self.task.task_id,
            "packet_fingerprint": PACKET_A,
            "gate_fingerprint": GATE_A,
            "gate_decision": "soft_block",
            "evidence_refs": ("evidence:gate",),
            "occurred_at": NOW,
        }
        values.update(changes)
        return values

    def decision_values(self, **changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "event_id": "event:decision:1",
            "task_id": self.task.task_id,
            "assurance_packet_fingerprint": PACKET_A,
            "gate_fingerprint": GATE_A,
            "gate_decision": "soft_block",
            "decision": "revise",
            "decision_source": "product_authority",
            "actor_ref": "actor:local-user",
            "reason": "Human observation is missing",
            "residual_risks": ("HWPX observation remains unobserved",),
            "follow_up": "Run the registered HWPX adapter",
            "evidence_refs": ("evidence:gate",),
            "occurred_at": NOW,
        }
        values.update(changes)
        return values

    def test_assurance_and_decision_are_canonical_projected_references(self) -> None:
        assurance = record_assurance_reference(self.events, **self.assurance_values())
        decision = record_task_decision(self.events, **self.decision_values())

        status = self.projections.project(self.task.task_id)

        self.assertEqual("ready", status.state)
        self.assertEqual(
            {
                "event_id": "event:assurance:1",
                "sequence": 2,
                "packet_fingerprint": PACKET_A,
                "gate_fingerprint": GATE_A,
                "gate_decision": "soft_block",
                "evidence_refs": ["evidence:gate"],
                "occurred_at": NOW,
            },
            status.projection["assurance"]["references"][0],
        )
        self.assertEqual(
            {
                "event_id": "event:decision:1",
                "sequence": 3,
                "assurance_packet_fingerprint": PACKET_A,
                "gate_fingerprint": GATE_A,
                "gate_decision": "soft_block",
                "decision": "revise",
                "decision_source": "product_authority",
                "actor_ref": "actor:local-user",
                "reason": "Human observation is missing",
                "residual_risks": ["HWPX observation remains unobserved"],
                "follow_up": "Run the registered HWPX adapter",
                "evidence_refs": ["evidence:gate"],
                "occurred_at": NOW,
            },
            status.projection["decision"],
        )
        self.assertEqual(PACKET_A, assurance.payload["packet_fingerprint"])
        self.assertEqual(PACKET_A, decision.payload["assurance_packet_fingerprint"])

    def test_same_event_id_is_idempotent_and_changed_content_conflicts(self) -> None:
        first = record_assurance_reference(self.events, **self.assurance_values())

        self.assertEqual(
            first,
            record_assurance_reference(self.events, **self.assurance_values()),
        )
        with self.assertRaisesRegex(EventConflict, "different content"):
            record_assurance_reference(
                self.events,
                **self.assurance_values(gate_decision="pass"),
            )

    def test_existing_decision_remains_idempotent_against_its_preceding_assurance(self) -> None:
        record_assurance_reference(self.events, **self.assurance_values())
        first = record_task_decision(self.events, **self.decision_values())
        record_assurance_reference(
            self.events,
            **self.assurance_values(
                event_id="event:assurance:2",
                packet_fingerprint=PACKET_B,
                gate_fingerprint=GATE_B,
                gate_decision="pass",
            ),
        )

        repeated = record_task_decision(self.events, **self.decision_values())

        self.assertEqual(first, repeated)
        self.assertEqual(4, self.events.head_sequence(self.task.task_id))

    def test_hard_block_cannot_be_accepted_or_risk_accepted(self) -> None:
        record_assurance_reference(
            self.events,
            **self.assurance_values(gate_decision="hard_block"),
        )
        for decision in ("accept", "risk_acceptance"):
            with self.subTest(decision=decision), self.assertRaisesRegex(
                ValueError, "Hard Block"
            ):
                record_task_decision(
                    self.events,
                    **self.decision_values(
                        gate_decision="hard_block", decision=decision
                    ),
                )

    def test_unsupported_assurance_event_version_fails_projection(self) -> None:
        assurance = record_assurance_reference(self.events, **self.assurance_values())
        unsupported = replace(
            EventDraft(
                event_id=assurance.event_id,
                task_id=assurance.task_id,
                event_type=assurance.event_type,
                event_version=assurance.event_version,
                occurred_at=assurance.occurred_at,
                payload=assurance.payload,
                collection_method=assurance.collection_method,
                redaction_status=assurance.redaction_status,
            ),
            event_id="event:assurance:unsupported",
            event_version=99,
        )
        self.events.append(unsupported, lambda payload: payload)

        status = self.projections.project(self.task.task_id)

        self.assertEqual("failed", status.state)
        self.assertEqual(2, status.projected_sequence)
        self.assertIn("unsupported event", status.last_error)

    def test_decision_command_rejects_each_stale_assurance_identity_before_append(self) -> None:
        record_assurance_reference(self.events, **self.assurance_values())
        record_assurance_reference(
            self.events,
            **self.assurance_values(
                event_id="event:assurance:2",
                packet_fingerprint=PACKET_B,
                gate_fingerprint=GATE_B,
                gate_decision="pass",
            ),
        )
        attacks = (
            {"assurance_packet_fingerprint": PACKET_A},
            {
                "assurance_packet_fingerprint": PACKET_B,
                "gate_fingerprint": GATE_A,
                "gate_decision": "pass",
            },
            {
                "assurance_packet_fingerprint": PACKET_B,
                "gate_fingerprint": GATE_B,
                "gate_decision": "soft_block",
            },
        )
        for attack in attacks:
            values = {
                "assurance_packet_fingerprint": PACKET_B,
                "gate_fingerprint": GATE_B,
                "gate_decision": "pass",
            }
            values.update(attack)
            with self.subTest(attack=attack), self.assertRaisesRegex(
                ValueError, "latest Assurance"
            ):
                record_task_decision(
                    self.events,
                    **self.decision_values(**values),
                )
            self.assertEqual(3, self.events.head_sequence(self.task.task_id))

    def test_forged_pass_cannot_append_acceptance_after_latest_hard_block(self) -> None:
        record_assurance_reference(
            self.events,
            **self.assurance_values(gate_decision="hard_block"),
        )

        with self.assertRaisesRegex(ValueError, "latest Assurance|Hard Block"):
            record_task_decision(
                self.events,
                **self.decision_values(
                    gate_decision="pass",
                    decision="accept",
                ),
            )

        self.assertEqual(2, self.events.head_sequence(self.task.task_id))
        self.assertEqual(
            ["task.created", "assurance.evaluated"],
            [event.event_type for event in self.events.list_for_task(self.task.task_id)],
        )


if __name__ == "__main__":
    unittest.main()

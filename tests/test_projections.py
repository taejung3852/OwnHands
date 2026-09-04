from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from devharness.catalog import Catalog
from devharness.events import EventDraft, EventLog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths
from devharness.projections import ProjectionEngine


def identity_redactor(payload: dict) -> dict:
    return payload


class ProjectionEngineTests(unittest.TestCase):
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
        self.engine = ProjectionEngine(self.catalog, self.events)
        self.next_event = 1

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def append_event(
        self,
        event_type: str,
        payload: dict,
        *,
        event_version: int = 1,
    ) -> None:
        event_number = self.next_event
        self.next_event += 1
        self.events.append(
            EventDraft(
                event_id=f"projection-event-{event_number}",
                task_id=self.task.task_id,
                event_type=event_type,
                event_version=event_version,
                occurred_at=f"2026-09-04T12:00:{event_number:02d}+00:00",
                payload=payload,
                collection_method="projection-test",
                redaction_status="not_needed",
            ),
            identity_redactor,
        )

    def test_rebuild_recreates_the_same_projection(self) -> None:
        self.append_event("task.created", {"mode": "managed"})
        self.append_event(
            "evidence.recorded",
            {"evidence_id": "evidence-1", "evidence_type": "test_execution"},
        )
        expected = self.engine.project(self.task.task_id)

        rebuilt = self.engine.rebuild(self.task.task_id)

        self.assertEqual("ready", rebuilt.state)
        self.assertEqual(expected.projected_sequence, rebuilt.projected_sequence)
        self.assertEqual(expected.projection, rebuilt.projection)

    def test_head_ahead_of_projection_is_stale_until_replayed(self) -> None:
        self.append_event("task.created", {"mode": "managed"})
        self.engine.project(self.task.task_id)
        self.assertTrue(self.engine.freshness(self.task.task_id).is_fresh)

        self.append_event(
            "evidence.recorded",
            {"evidence_id": "evidence-1", "evidence_type": "test_execution"},
        )
        stale = self.engine.freshness(self.task.task_id)

        self.assertFalse(stale.is_fresh)
        self.assertEqual((2, 1), (stale.event_head, stale.projected_sequence))
        self.assertEqual("unobserved", stale.collection_completeness)

        self.engine.project(self.task.task_id)
        self.assertTrue(self.engine.freshness(self.task.task_id).is_fresh)

    def test_unknown_event_version_fails_without_advancing(self) -> None:
        self.append_event("task.created", {"mode": "managed"})
        self.append_event("evidence.recorded", {"evidence_id": "evidence-1"}, event_version=99)

        status = self.engine.project(self.task.task_id)
        freshness = self.engine.freshness(self.task.task_id)

        self.assertEqual("failed", status.state)
        self.assertEqual(1, status.projected_sequence)
        self.assertIn("unsupported event", status.last_error)
        self.assertFalse(freshness.is_fresh)
        self.assertEqual("failed", freshness.projection_state)

    def test_malformed_known_event_records_failure(self) -> None:
        self.append_event("evidence.recorded", {"evidence_type": "test_execution"})

        status = self.engine.project(self.task.task_id)

        self.assertEqual("failed", status.state)
        self.assertEqual(0, status.projected_sequence)
        self.assertIn("evidence_id", status.last_error)

    def test_purge_updates_active_and_purged_evidence(self) -> None:
        self.append_event(
            "evidence.recorded",
            {"evidence_id": "evidence-1", "evidence_type": "test_execution"},
        )
        self.append_event("evidence.purged", {"evidence_id": "evidence-1"})

        status = self.engine.project(self.task.task_id)

        self.assertEqual([], status.projection["evidence"]["active_ids"])
        self.assertEqual(["evidence-1"], status.projection["evidence"]["purged_ids"])

    def test_unknown_task_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown task"):
            self.engine.project("missing-task")


if __name__ == "__main__":
    unittest.main()

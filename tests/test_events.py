from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from devharness.catalog import Catalog
from devharness.events import EventConflict, EventDraft, EventLog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths


def redact_payload(payload: dict) -> dict:
    redacted = dict(payload)
    if "token" in redacted:
        redacted["token"] = "[REDACTED]"
    return redacted


def raw_event_fingerprint(
    row: sqlite3.Row,
    payload: dict,
    sequence: int,
    *,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> str:
    document = {
        "event_id": event_id or row["event_id"],
        "task_id": row["task_id"],
        "event_type": row["event_type"],
        "event_version": row["event_version"],
        "occurred_at": occurred_at or row["occurred_at"],
        "payload": payload,
        "collection_method": row["collection_method"],
        "redaction_status": row["redaction_status"],
        "sequence": sequence,
    }
    canonical = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class EventLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.paths = DataPaths.resolve(Path(self.temporary_directory.name) / "data")
        self.catalog = Catalog.open(self.paths)
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
        self.log = EventLog(self.catalog)
        self.draft = EventDraft(
            event_id="event-1",
            task_id=self.task.task_id,
            event_type="task.created",
            event_version=1,
            occurred_at="2026-09-04T12:00:00+00:00",
            payload={"mode": "managed"},
            collection_method="m1-test",
            redaction_status="not_needed",
        )

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def test_task_sequence_is_monotonic(self) -> None:
        first = self.log.append(self.draft, redact_payload)
        second = self.log.append(
            replace(self.draft, event_id="event-2", event_type="tool.completed"),
            redact_payload,
        )

        self.assertEqual((1, 2), (first.sequence, second.sequence))
        self.assertEqual(2, self.log.head_sequence(self.task.task_id))
        self.assertEqual([first, second], self.log.list_for_task(self.task.task_id))

    def test_duplicate_id_is_idempotent_only_for_identical_event(self) -> None:
        first = self.log.append(self.draft, redact_payload)

        self.assertEqual(first, self.log.append(self.draft, redact_payload))
        with self.assertRaisesRegex(EventConflict, "different content"):
            self.log.append(
                replace(self.draft, payload={"mode": "imported"}), redact_payload
            )
        self.assertEqual(1, self.log.head_sequence(self.task.task_id))

    def test_secret_is_redacted_before_storage(self) -> None:
        event = self.log.append(
            replace(
                self.draft,
                event_type="tool.completed",
                payload={"token": "m1-secret-marker", "safe": True},
                redaction_status="redacted",
            ),
            redact_payload,
        )

        self.assertEqual("[REDACTED]", event.payload["token"])
        self.assertNotIn(
            b"m1-secret-marker",
            self.catalog.path.read_bytes(),
        )

    def test_redactor_failure_leaves_no_event(self) -> None:
        def fail_redaction(_payload: dict) -> dict:
            raise RuntimeError("redaction failed")

        with self.assertRaisesRegex(RuntimeError, "redaction failed"):
            self.log.append(self.draft, fail_redaction)

        self.assertEqual([], self.log.list_for_task(self.task.task_id))

    def test_event_rows_are_append_only(self) -> None:
        self.log.append(self.draft, redact_payload)

        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.catalog.connection.execute(
                "UPDATE events SET event_type='changed' WHERE event_id='event-1'"
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.catalog.connection.execute(
                "DELETE FROM events WHERE event_id='event-1'"
            )

    def test_event_read_recomputes_fingerprint_after_raw_payload_tampering(self) -> None:
        self.log.append(self.draft, redact_payload)
        self.catalog.connection.execute("DROP TRIGGER events_no_update")
        self.catalog.connection.execute(
            "UPDATE events SET payload_json=? WHERE event_id=?",
            ('{"mode":"imported"}', self.draft.event_id),
        )

        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.log.list_for_task(self.task.task_id)

    def test_event_head_recomputes_fingerprint_after_raw_metadata_tampering(self) -> None:
        self.log.append(self.draft, redact_payload)
        self.catalog.connection.execute("DROP TRIGGER events_no_update")
        self.catalog.connection.execute(
            "UPDATE events SET collection_method=? WHERE event_id=?",
            ("forged-collector", self.draft.event_id),
        )

        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.log.head_sequence(self.task.task_id)

    def test_event_read_fails_closed_after_raw_sequence_gap(self) -> None:
        self.log.append(self.draft, redact_payload)
        self.log.append(
            replace(self.draft, event_id="event-2", event_type="tool.completed"),
            redact_payload,
        )
        self.catalog.connection.execute("DROP TRIGGER events_no_update")
        self.catalog.connection.execute(
            "UPDATE events SET sequence=3 WHERE event_id='event-2'"
        )

        with self.assertRaisesRegex(ValueError, "fingerprint|sequence integrity"):
            self.log.list_for_task(self.task.task_id)

    def test_unknown_task_and_invalid_envelope_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown task"):
            self.log.append(replace(self.draft, task_id="missing"), redact_payload)
        with self.assertRaisesRegex(ValueError, "event_version"):
            self.log.append(replace(self.draft, event_version=0), redact_payload)
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.log.append(
                replace(self.draft, occurred_at="2026-09-04T12:00:00"),
                redact_payload,
            )

    def test_task_created_mode_must_match_immutable_task_snapshot(self) -> None:
        with self.assertRaisesRegex(ValueError, "task.created.*mode"):
            self.log.append(
                replace(self.draft, payload={"mode": "imported"}),
                redact_payload,
            )

        self.assertEqual(0, self.log.head_sequence(self.task.task_id))

    def test_task_created_can_only_be_the_first_event_once(self) -> None:
        self.log.append(self.draft, redact_payload)

        with self.assertRaisesRegex(ValueError, "task.created.*sequence 1|exactly once"):
            self.log.append(
                replace(self.draft, event_id="event-2"),
                redact_payload,
            )

        self.assertEqual(1, self.log.head_sequence(self.task.task_id))

    def test_raw_resigned_task_created_mode_mismatch_is_rejected_on_read(self) -> None:
        self.log.append(self.draft, redact_payload)
        self.catalog.connection.execute("DROP TRIGGER events_no_update")
        row = self.catalog.connection.execute(
            "SELECT * FROM events WHERE event_id=?", (self.draft.event_id,)
        ).fetchone()
        payload = {"mode": "imported"}
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        fingerprint = raw_event_fingerprint(row, payload, 1)
        self.catalog.connection.execute(
            """
            UPDATE events SET payload_json=?, fingerprint=?
            WHERE event_id=?
            """,
            (payload_json, fingerprint, self.draft.event_id),
        )

        with self.assertRaisesRegex(ValueError, "task.created.*mode"):
            self.log.list_for_task(self.task.task_id)

    def test_raw_resigned_duplicate_task_created_is_rejected_on_read(self) -> None:
        self.log.append(self.draft, redact_payload)
        first = self.catalog.connection.execute(
            "SELECT * FROM events WHERE event_id=?", (self.draft.event_id,)
        ).fetchone()
        payload = {"mode": "managed"}
        fingerprint = raw_event_fingerprint(
            first,
            payload,
            2,
            event_id="event-2",
            occurred_at="2026-09-04T12:00:01+00:00",
        )
        self.catalog.connection.execute(
            """
            INSERT INTO events(
                event_id, task_id, sequence, event_type, event_version,
                occurred_at, payload_json, collection_method,
                redaction_status, fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "event-2",
                self.task.task_id,
                2,
                "task.created",
                1,
                "2026-09-04T12:00:01+00:00",
                json.dumps(payload, separators=(",", ":"), sort_keys=True),
                "m1-test",
                "not_needed",
                fingerprint,
            ),
        )

        with self.assertRaisesRegex(ValueError, "task.created.*sequence 1|exactly once"):
            self.log.list_for_task(self.task.task_id)


if __name__ == "__main__":
    unittest.main()

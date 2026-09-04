from __future__ import annotations

import hashlib
import stat
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from devharness.catalog import Catalog
from devharness.evidence import (
    EvidenceConflict,
    EvidenceDraft,
    EvidenceStore,
    RetentionPolicy,
)
from devharness.events import EventLog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths


def redact_bytes(content: bytes) -> bytes:
    return content.replace(b"m1-secret-marker", b"[REDACTED]")


class EvidenceStoreTests(unittest.TestCase):
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
        self.events = EventLog(self.catalog)
        self.store = EvidenceStore(self.catalog, self.events)
        self.draft = EvidenceDraft(
            evidence_id="evidence-1",
            task_id=self.task.task_id,
            requirement_id="test-run",
            evidence_type="test_execution",
            subject_ref="test-selection.synthetic",
            exact_scope="tests/hwpx-package",
            result="pass",
            basis="observed",
            fields={
                "command": "python -m unittest tests.hwpx",
                "environment": "synthetic-local",
                "target_commit": "abc123",
                "selection_scope": "HWPX package inspection",
                "result": "pass",
            },
            content=b"raw package bytes: m1-secret-marker",
            collection_method="synthetic-fixture",
            redaction_status="redacted",
        )

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def test_content_is_redacted_hashed_and_stored_with_private_permissions(self) -> None:
        record = self.store.put(self.draft, redact_bytes)
        expected = b"raw package bytes: [REDACTED]"

        self.assertEqual(hashlib.sha256(expected).hexdigest(), record.content_hash)
        self.assertEqual(expected, self.store.read_content(record.evidence_id))
        self.assertEqual(0o700, stat.S_IMODE(self.paths.objects.stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE(record.object_path.stat().st_mode))
        self.assertNotIn(b"m1-secret-marker", record.object_path.read_bytes())
        self.assertEqual(
            "evidence.recorded",
            self.events.list_for_task(self.task.task_id)[0].event_type,
        )

    def test_content_hash_deduplicates_objects_but_keeps_distinct_metadata(self) -> None:
        first = self.store.put(self.draft, redact_bytes)
        second = self.store.put(
            replace(self.draft, evidence_id="evidence-2"), redact_bytes
        )

        self.assertEqual(first.content_hash, second.content_hash)
        self.assertEqual(first.object_path, second.object_path)
        self.assertEqual(1, len([path for path in self.paths.objects.rglob("*") if path.is_file()]))
        self.assertEqual(2, len(self.store.list_for_task(self.task.task_id)))

    def test_duplicate_evidence_id_requires_identical_metadata_and_content(self) -> None:
        first = self.store.put(self.draft, redact_bytes)

        self.assertEqual(first, self.store.put(self.draft, redact_bytes))
        with self.assertRaisesRegex(EvidenceConflict, "different content"):
            self.store.put(replace(self.draft, result="fail"), redact_bytes)
        self.assertEqual(1, len(self.store.list_for_task(self.task.task_id)))

    def test_required_metadata_and_authoritative_resolution(self) -> None:
        record = self.store.put(self.draft, redact_bytes)
        resolved = self.store.resolve(record.evidence_id)

        self.assertEqual("test_execution", resolved.evidence_type)
        self.assertEqual("test-selection.synthetic", resolved.subject_ref)
        self.assertEqual("tests/hwpx-package", resolved.exact_scope)
        self.assertEqual(self.draft.fields, resolved.fields)

        with self.assertRaisesRegex(ValueError, "fields"):
            self.store.put(replace(self.draft, evidence_id="empty-fields", fields={}), redact_bytes)
        with self.assertRaisesRegex(ValueError, "sensitive field"):
            self.store.put(
                replace(
                    self.draft,
                    evidence_id="sensitive-fields",
                    fields={"api_token": "do-not-store"},
                ),
                redact_bytes,
            )
        objects_before_unknown_task = {
            path for path in self.paths.objects.rglob("*") if path.is_file()
        }
        with self.assertRaisesRegex(ValueError, "unknown task"):
            self.store.put(replace(self.draft, evidence_id="foreign", task_id="missing"), redact_bytes)
        self.assertEqual(
            objects_before_unknown_task,
            {path for path in self.paths.objects.rglob("*") if path.is_file()},
        )

    def test_default_retention_never_deletes_automatically(self) -> None:
        self.assertEqual(
            RetentionPolicy(mode="keep_until_user_deletes", days=None),
            self.store.retention(),
        )
        with self.assertRaisesRegex(ValueError, "days"):
            self.store.set_retention(RetentionPolicy(mode="days", days=None))

        self.store.set_retention(RetentionPolicy(mode="days", days=30))
        self.assertEqual(RetentionPolicy(mode="days", days=30), self.store.retention())
        self.store.put(self.draft, redact_bytes)
        self.assertEqual(1, len(self.store.list_for_task(self.task.task_id)))

    def test_explicit_purge_removes_only_unreferenced_object_and_appends_tombstone(self) -> None:
        first = self.store.put(self.draft, redact_bytes)
        second = self.store.put(
            replace(self.draft, evidence_id="evidence-2"), redact_bytes
        )

        self.store.purge(first.evidence_id, "user request")
        self.assertTrue(second.object_path.exists())
        with self.assertRaisesRegex(ValueError, "purged"):
            self.store.resolve(first.evidence_id)

        self.store.purge(second.evidence_id, "user request")
        self.assertFalse(second.object_path.exists())
        self.assertEqual(
            ["evidence.recorded", "evidence.recorded", "evidence.purged", "evidence.purged"],
            [event.event_type for event in self.events.list_for_task(self.task.task_id)],
        )

        with self.assertRaisesRegex(ValueError, "reason"):
            self.store.purge("missing", "")

    def test_hash_mismatch_is_detected_on_read(self) -> None:
        record = self.store.put(self.draft, redact_bytes)
        record.object_path.write_bytes(b"tampered")

        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.store.read_content(record.evidence_id)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from devharness.catalog import Catalog
from devharness.dashboard_sources import resolve_evidence
from devharness.evidence import EvidenceDraft, EvidenceStore
from devharness.events import EventDraft, EventLog
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths
from devharness.dashboard_view import _direct_evidence


NOW = "2026-09-06T12:00:00+00:00"
PACKET = "sha256:" + "a" * 64


class DashboardEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="/tmp")
        self.paths = DataPaths.resolve(Path(self.temporary.name) / "data")
        self.catalog = Catalog.open(self.paths)
        registry = IdentityRegistry(self.catalog)
        project = registry.register_project("file:///repo")
        worktree = registry.register_worktree(project.project_id, "file:///repo/main")
        self.task = registry.create_task(
            worktree.worktree_id, "managed", "abc123", "main", "/repo", "local-test"
        )
        self.other_task = registry.create_task(
            worktree.worktree_id, "managed", "abc123", "main", "/repo", "local-test"
        )
        self.events = EventLog(self.catalog)
        for index, task in enumerate((self.task, self.other_task), 1):
            self.events.append(
                EventDraft(
                    event_id=f"event:task:{index}", task_id=task.task_id,
                    event_type="task.created", event_version=1, occurred_at=NOW,
                    payload={"mode": "managed"}, collection_method="test",
                    redaction_status="not_needed",
                ),
                lambda payload: payload,
            )
        self.store = EvidenceStore(self.catalog, self.events)

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary.cleanup()

    def put(self, evidence_id: str, *, task_id: str | None = None, packet: str = PACKET):
        return self.store.put(
            EvidenceDraft(
                evidence_id=evidence_id,
                task_id=task_id or self.task.task_id,
                requirement_id="M5-04",
                evidence_type="test_execution",
                subject_ref="subject:dashboard",
                exact_scope="tests.dashboard",
                result="pass",
                basis="observed",
                fields={
                    "packet_fingerprint": packet,
                    "selection_scope": "tests.dashboard",
                    "safe_note": "must be omitted",
                },
                content=f"trusted evidence: {evidence_id}".encode(),
                collection_method="dashboard-test",
                redaction_status="redacted",
            ),
            bytes,
        )

    def assurance(self, *refs: str) -> dict:
        return {"fingerprint": PACKET, "evidence_refs": list(refs)}

    def test_unregistered_m4_reference_remains_reference_only(self) -> None:
        view, content = resolve_evidence(
            self.store,
            task_id=self.task.task_id,
            evidence_id="evidence:m4:logical",
            assurance_packet=self.assurance("evidence:m4:logical"),
        )

        self.assertEqual("reference_only", view.reference_kind)
        self.assertFalse(view.raw_available)
        self.assertIsNone(content)

    def test_registered_reference_requires_task_packet_and_integrity_before_disclosure(self) -> None:
        record = self.put("evidence:m4:registered")

        metadata_view, metadata_content = resolve_evidence(
            self.store, task_id=self.task.task_id,
            evidence_id=record.evidence_id,
            assurance_packet=self.assurance(record.evidence_id),
        )
        raw_view, raw_content = resolve_evidence(
            self.store, task_id=self.task.task_id,
            evidence_id=record.evidence_id,
            assurance_packet=self.assurance(record.evidence_id),
            disclose_raw=True,
        )

        self.assertEqual("store", metadata_view.reference_kind)
        self.assertTrue(metadata_view.raw_available)
        self.assertIsNone(metadata_content)
        self.assertTrue(raw_view.raw_available)
        self.assertEqual(b"trusted evidence: evidence:m4:registered", raw_content)
        self.assertNotIn("object_path", raw_view.metadata)
        self.assertNotIn("safe_note", raw_view.metadata)
        self.assertEqual(PACKET, raw_view.metadata["packet_fingerprint"])

    def test_cross_task_wrong_packet_purge_and_unsafe_identifiers_fail_closed(self) -> None:
        cross = self.put("evidence:cross-task", task_id=self.other_task.task_id)
        wrong = self.put("evidence:wrong-packet", packet="sha256:" + "b" * 64)
        purged = self.put("evidence:purged")
        self.store.purge(purged.evidence_id, "test")

        cases = (
            (cross.evidence_id, self.assurance(cross.evidence_id)),
            (wrong.evidence_id, self.assurance(wrong.evidence_id)),
            (purged.evidence_id, self.assurance(purged.evidence_id)),
            ("evidence:../secret", self.assurance("evidence:../secret")),
            ("evidence%2Fsecret", self.assurance("evidence%2Fsecret")),
        )
        for evidence_id, packet in cases:
            with self.subTest(evidence_id=evidence_id), self.assertRaises(ValueError):
                resolve_evidence(
                    self.store, task_id=self.task.task_id,
                    evidence_id=evidence_id, assurance_packet=packet,
                    disclose_raw=True,
                )

    def test_metadata_masks_embedded_private_values_and_preserves_public_context(self) -> None:
        draft = EvidenceDraft(
            evidence_id="evidence:metadata:values",
            task_id=self.task.task_id,
            requirement_id="M5-04",
            evidence_type="test_execution",
            subject_ref="subject:dashboard",
            exact_scope="raw command and arbitrary user input",
            result="pass",
            basis="observed",
            fields={},
            content=b"explicit raw disclosure only",
            collection_method="dashboard-test",
            redaction_status="redacted",
        )
        cases = (
            ("run /Users/private/worktree/bin/python", "run [redacted-local-path]"),
            ("path=/private/data/root", "path=[redacted-local-path]"),
            ("cwd:/Users/private/worktree", "cwd:[redacted-local-path]"),
            (r"run C:\Users\private\python.exe", "run [redacted-local-path]"),
            ("file:///private/data/root", "[redacted-local-path]"),
            ('--token "quoted-private-value"', "[redacted-sensitive-value]"),
            ("Authorization: Bearer private-value", "[redacted-sensitive-value]"),
            ("Bearer private-value", "[redacted-sensitive-value]"),
            ("bEaReR\tprivate-value", "[redacted-sensitive-value]"),
            ("bearer", "bearer"),
            ("bearer-token policy; wheelbearer value", "bearer-token policy; wheelbearer value"),
            ('{"api_key": "private-value"}', "[redacted-sensitive-value]"),
            ("raw=<script>private-value</script>", "[redacted-sensitive-value]"),
            (
                "tests/dashboard.py; 3/4 pass; https://example.com/docs",
                "tests/dashboard.py; 3/4 pass; https://example.com/docs",
            ),
            (
                {
                    "draw_count": 4,
                    "raw_payload": "private-value",
                    "command_output": "private-value",
                    "selection": "tests.dashboard",
                },
                {"draw_count": 4, "selection": "tests.dashboard"},
            ),
        )
        for index, (value, expected) in enumerate(cases):
            with self.subTest(value=value):
                record = self.store.put(
                    replace(
                        draft,
                        evidence_id=f"evidence:metadata:values:{index}",
                        fields={"selection_scope": value, "tool": "python", "unknown": "omit-me"},
                    ),
                    bytes,
                )
                view, content = resolve_evidence(
                    self.store, task_id=self.task.task_id,
                    evidence_id=record.evidence_id, assurance_packet=None,
                )
                self.assertEqual(expected, view.metadata["selection_scope"])
                self.assertEqual("python", view.metadata["tool"])
                self.assertNotIn("exact_scope", view.metadata)
                self.assertNotIn("unknown", view.metadata)
                self.assertIsNone(content)

    def test_hash_size_and_symlink_objects_fail_closed(self) -> None:
        for attack in ("hash", "size", "symlink"):
            with self.subTest(attack=attack):
                record = self.put(f"evidence:attack:{attack}")
                if attack == "hash":
                    record.object_path.write_bytes(b"tampered")
                elif attack == "size":
                    self.catalog.connection.execute(
                        "DROP TRIGGER evidence_canonical_fields_immutable"
                    )
                    self.catalog.connection.execute(
                        "UPDATE evidence SET content_size=content_size+1 WHERE evidence_id=?",
                        (record.evidence_id,),
                    )
                else:
                    target = Path(self.temporary.name) / "outside"
                    target.write_bytes(f"trusted evidence: {record.evidence_id}".encode())
                    record.object_path.unlink()
                    record.object_path.symlink_to(target)
                with self.assertRaises(ValueError):
                    resolve_evidence(
                        self.store, task_id=self.task.task_id,
                        evidence_id=record.evidence_id,
                        assurance_packet=self.assurance(record.evidence_id),
                        disclose_raw=True,
                    )

    def test_direct_human_evidence_requires_complete_hwpx_contract_and_safe_object(self) -> None:
        incomplete = self.store.put(
            EvidenceDraft(
                evidence_id="evidence:direct:unrelated",
                task_id=self.task.task_id,
                requirement_id="M5-06",
                evidence_type="direct_feature_probe",
                subject_ref="subject:generic",
                exact_scope="generic feature",
                result="pass",
                basis="observed",
                fields={"human_observation": True, "adapter": "generic"},
                content=b"generic observation",
                collection_method="test",
                redaction_status="redacted",
            ),
            bytes,
        )
        self.assertIsNone(_direct_evidence(self.store, [incomplete], self.task))

        valid = self.store.put(
            EvidenceDraft(
                evidence_id="evidence:direct:hwpx",
                task_id=self.task.task_id,
                requirement_id="M5-06",
                evidence_type="direct_feature_probe",
                subject_ref="subject:hwpx:document",
                exact_scope="HWPX generated document",
                result="pass",
                basis="observed",
                fields={
                    "adapter": "hwpx",
                    "input": "source:document",
                    "expected": "expected:render",
                    "actual": "actual:render",
                    "environment": self.task.environment_ref,
                    "generated_files": ["artifact:rendered-document"],
                    "human_observation": "human confirmed rendering",
                },
                content=b"hwpx human observation",
                collection_method="registered-hwpx-adapter",
                redaction_status="redacted",
            ),
            bytes,
        )
        self.assertEqual(valid, _direct_evidence(self.store, [valid], self.task))
        outside = Path(self.temporary.name) / "outside-human"
        outside.write_bytes(b"hwpx human observation")
        valid.object_path.unlink()
        valid.object_path.symlink_to(outside)

        self.assertIsNone(_direct_evidence(self.store, [valid], self.task))


if __name__ == "__main__":
    unittest.main()

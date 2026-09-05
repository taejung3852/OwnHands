from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from devharness.catalog import Catalog
from devharness.evidence import EvidenceStore
from devharness.events import EventLog
from devharness.imported_tasks import ImportedTaskError, import_task
from devharness.paths import DataPaths
from devharness.projections import ProjectionEngine


FIXTURE_PATH = Path(__file__).parent / "fixtures/m3/imported-task.json"


def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def verdict(report: dict, claim_id: str) -> str:
    return next(
        result["verdict"]
        for result in report["claim_results"]
        if result["claim_id"] == claim_id
    )


class ImportedTaskTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.paths = DataPaths.resolve(
            Path(self.temporary_directory.name) / "imported-data"
        )
        self.catalog = Catalog.open(self.paths)

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def test_imported_task_observes_only_current_snapshot_diff_and_test(self) -> None:
        packet = import_task(fixture(), self.catalog)

        self.assertEqual("imported", packet["mode"])
        self.assertEqual("observed", packet["snapshot"]["basis"])
        self.assertEqual("observed", packet["current_diff"]["basis"])
        self.assertEqual("observed", packet["current_test"]["basis"])
        for control_name in (
            "config",
            "agents",
            "rules",
            "hooks",
            "sandbox",
            "approval",
        ):
            with self.subTest(control=control_name):
                checks = packet["controls"][control_name]
                for check_name in ("configured", "loaded", "enforced"):
                    self.assertEqual("not_run", checks[check_name]["result"])
                    self.assertEqual("unobserved", checks[check_name]["basis"])
                    self.assertEqual([], checks[check_name]["evidence_refs"])
        self.assertEqual(
            0,
            self.catalog.query_value("SELECT COUNT(*) FROM control_validations"),
        )

    def test_imported_managed_only_claims_are_not_evaluated(self) -> None:
        report = import_task(fixture(), self.catalog)["guarantee_report"]

        self.assertEqual("supported", verdict(report, "GM-011"))
        self.assertEqual("supported", verdict(report, "GM-013"))
        for claim_id in (
            "GM-002",
            "GM-003",
            "GM-004",
            "GM-005",
            "GM-006",
            "GM-007",
            "GM-014",
        ):
            with self.subTest(claim=claim_id):
                self.assertEqual("not_evaluated", verdict(report, claim_id))

    def test_import_rejects_desktop_ids_foreign_identity_stale_test_and_fabricated_history(self) -> None:
        attacks = []
        desktop = fixture()
        desktop["desktop_thread_id"] = "thread-private"
        attacks.append(("Desktop", desktop))
        for key in ("project_locator", "worktree_locator", "cwd"):
            foreign = fixture()
            foreign["snapshot"][key] = f"/foreign/{key}"
            attacks.append(("identity", foreign))
        stale_test = fixture()
        stale_test["current_test"]["target_commit"] = "f" * 40
        attacks.append(("test receipt", stale_test))
        fabricated_approval = fixture()
        fabricated_approval["past_approval"] = {"result": "pass"}
        attacks.append(("historical", fabricated_approval))
        fabricated_control = fixture()
        fabricated_control["historical_controls"] = {"sandbox": "enforced"}
        attacks.append(("historical", fabricated_control))
        duplicate_refs = fixture()
        duplicate_refs["references"].append(duplicate_refs["references"][0])
        attacks.append(("duplicate", duplicate_refs))
        raw_secret = fixture()
        raw_secret["snapshot"]["api_token"] = "synthetic-secret-value"
        attacks.append(("sensitive", raw_secret))
        tampered_diff = fixture()
        tampered_diff["current_diff"]["patch"] += "tampered\n"
        attacks.append(("diff hash", tampered_diff))

        for expected, attack in attacks:
            with self.subTest(expected=expected), self.assertRaisesRegex(
                ImportedTaskError, expected
            ):
                import_task(attack, self.catalog)

        self.assertEqual(0, self.catalog.query_value("SELECT COUNT(*) FROM tasks"))

    def test_direct_test_receipt_requires_execution_result_consistency(self) -> None:
        indirect = fixture()
        indirect["current_test"]["collection_method"] = "provided_summary"
        inconsistent = fixture()
        inconsistent["current_test"]["result"] = "pass"
        inconsistent["current_test"]["exit_code"] = 3

        with self.assertRaisesRegex(ImportedTaskError, "direct"):
            import_task(indirect, self.catalog)
        with self.assertRaisesRegex(ImportedTaskError, "test receipt"):
            import_task(inconsistent, self.catalog)

    def test_imported_evidence_is_private_outside_snapshot_and_projection_is_fresh(self) -> None:
        packet = import_task(fixture(), self.catalog)
        events = EventLog(self.catalog)
        store = EvidenceStore(self.catalog, events)

        self.assertEqual(3, len(packet["evidence_refs"]))
        for evidence_id in packet["evidence_refs"]:
            record = store.resolve(evidence_id)
            self.assertFalse(
                record.object_path.is_relative_to(
                    Path(fixture()["snapshot"]["cwd"])
                )
            )
            self.assertEqual(0o600, os.stat(record.object_path).st_mode & 0o777)
        event_records = events.list_for_task(packet["task_id"])
        self.assertEqual(
            list(range(1, len(event_records) + 1)),
            [record.sequence for record in event_records],
        )
        projection = ProjectionEngine(self.catalog, events).project(packet["task_id"])
        freshness = ProjectionEngine(self.catalog, events).freshness(packet["task_id"])
        self.assertEqual("ready", projection.state)
        self.assertTrue(freshness.is_fresh)


if __name__ == "__main__":
    unittest.main()

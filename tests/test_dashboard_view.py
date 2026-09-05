from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from devharness.catalog import Catalog
from devharness.dashboard_view import _visible_result, assemble_task_review
from devharness.evidence import EvidenceStore
from devharness.events import EventLog
from devharness.identity import TaskIdentity
from devharness.m4_review import run_m4_fixture
from devharness.paths import DataPaths
from devharness.projections import Freshness, ProjectionStatus
from tests.test_dashboard_identity import m3_packet


NOW = "2026-09-06T12:00:00+00:00"


class DashboardViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir="/tmp")
        root = Path(self.temporary.name)
        run_m4_fixture(root / "m4-raw", root / "packet.json", root / "review.html", observed_at=NOW)
        self.packet = json.loads((root / "packet.json").read_text(encoding="utf-8"))
        identity = self.packet["task"]
        self.task = TaskIdentity(
            task_id=identity["task_id"], project_id=identity["project_id"],
            worktree_id=identity["worktree_id"], mode=identity["mode"],
            commit=self.packet["restore_point"]["start_commit"], branch="main", cwd="/repo",
            environment_ref=identity["environment_ref"], created_at=NOW,
        )
        paths = DataPaths.resolve(root / "data")
        self.catalog = Catalog.open(paths)
        self.events = EventLog(self.catalog)
        self.store = EvidenceStore(self.catalog, self.events)
        self.projection = ProjectionStatus(
            task_id=self.task.task_id, state="ready", projected_sequence=0,
            projection={}, last_error=None, updated_at=NOW,
        )
        self.freshness = Freshness(
            task_id=self.task.task_id, event_head=0, projected_sequence=0,
            projection_state="ready", is_fresh=True,
            collection_completeness="unobserved", last_error=None,
        )

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary.cleanup()

    def assemble(self, **changes):
        values = {
            "task": self.task,
            "events": self.events,
            "projection": self.projection,
            "freshness": self.freshness,
            "evidence_store": self.store,
            "baseline": None,
            "context_status": None,
            "execution_contract": self.packet["contract_snapshot"],
            "m3_packet": m3_packet(),
            "assurance_packet": self.packet,
            "guarantee_report": None,
            "assembled_at": NOW,
        }
        values.update(changes)
        return assemble_task_review(**values)

    def test_progressive_summary_and_missing_sources_do_not_invent_success(self) -> None:
        view = self.assemble()

        self.assertEqual(("summary", "trace", "evidence", "decision"), view.summary["disclosure_order"])
        self.assertEqual("not_evaluated", view.guarantees[0]["status"])
        direct = next(row for row in view.verification if row["kind"] == "direct_feature_validation")
        self.assertEqual("unobserved", direct["basis"])
        self.assertEqual("fresh", view.freshness["state"])
        self.assertEqual("unobserved", view.completeness["state"])
        self.assertFalse(view.decision["submission_allowed"])

    def test_relation_priority_and_diagram_are_source_derived_only(self) -> None:
        view = self.assemble()

        self.assertTrue(view.relations)
        self.assertIn("required", {relation["priority"] for relation in view.relations})
        self.assertEqual("observed", view.diagram["state"])
        relationless = json.loads(json.dumps(self.packet))
        relationless["impact"]["relations"] = []
        relationless_view = self.assemble(assurance_packet=None, execution_contract=None)
        self.assertEqual("unobserved", relationless_view.diagram["state"])

    def test_assembly_is_deterministic_and_does_not_write_catalog_or_files(self) -> None:
        before_catalog = self.catalog.connection.total_changes
        before_files = sorted(
            path.relative_to(self.catalog.paths.root)
            for path in self.catalog.paths.root.rglob("*") if path.is_file()
        )

        first = self.assemble()
        second = self.assemble()

        after_files = sorted(
            path.relative_to(self.catalog.paths.root)
            for path in self.catalog.paths.root.rglob("*") if path.is_file()
        )
        self.assertEqual(first, second)
        self.assertEqual(before_catalog, self.catalog.connection.total_changes)
        self.assertEqual(before_files, after_files)

    def test_visible_verification_vocabulary_preserves_all_six_states(self) -> None:
        self.assertEqual(
            {
                "passed",
                "failed",
                "not_run",
                "no_adequate_test",
                "inconclusive",
                "unknown",
            },
            {
                _visible_result("pass"),
                _visible_result("fail"),
                _visible_result("not_run"),
                "no_adequate_test",
                _visible_result("inconclusive"),
                _visible_result("missing"),
            },
        )

    def test_tampered_contract_goal_cannot_enter_summary_or_completeness(self) -> None:
        tampered = copy.deepcopy(self.packet["contract_snapshot"])
        tampered["task"]["goal"] = "forged success summary"

        view = self.assemble(execution_contract=tampered)

        self.assertIsNone(view.summary["goal"])
        self.assertIn("execution_contract", view.completeness["missing"])

        malformed = copy.deepcopy(self.packet["contract_snapshot"])
        malformed["task"]["goal"] = object()
        malformed_view = self.assemble(execution_contract=malformed)
        self.assertIsNone(malformed_view.summary["goal"])
        self.assertIn("execution_contract", malformed_view.completeness["missing"])


if __name__ == "__main__":
    unittest.main()

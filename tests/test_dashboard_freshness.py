from __future__ import annotations

import unittest
from dataclasses import replace

from devharness.evidence import EvidenceDraft
from devharness.events import EventDraft
from devharness.m3_review import build_review_packet
from tests.test_dashboard_view import NOW, DashboardViewTests as _DashboardViewTests
from tests.test_m3_review import imported_packet, managed_packet, raw_receipt


class DashboardFreshnessTests(unittest.TestCase):
    setUp = _DashboardViewTests.setUp
    tearDown = _DashboardViewTests.tearDown
    assemble = _DashboardViewTests.assemble

    def test_freshness_and_collection_completeness_are_independent(self) -> None:
        fresh_but_incomplete = self.assemble()

        stale = replace(
            self.freshness,
            event_head=2,
            projected_sequence=1,
            is_fresh=False,
        )
        guarantee = {
            "report_version": "1.0",
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "mode": self.task.mode,
                "target_commit": self.task.commit,
                "environment_ref": self.task.environment_ref,
            },
            "claim_results": [
                {"claim_id": "GM-016", "verdict": "supported", "permitted_statement": "directly validated"}
            ],
        }
        stale_but_complete = self.assemble(
            freshness=stale,
            m3_packet=None,
            guarantee_report=guarantee,
        )

        self.assertEqual("fresh", fresh_but_incomplete.freshness["state"])
        self.assertEqual("unobserved", fresh_but_incomplete.completeness["state"])
        self.assertEqual("stale", stale_but_complete.freshness["state"])
        self.assertEqual("unobserved", stale_but_complete.completeness["state"])
        self.assertFalse(stale_but_complete.decision["submission_allowed"])

    def test_projection_failure_is_not_presented_as_ordinary_lag(self) -> None:
        failure = replace(
            self.freshness,
            projection_state="failed",
            is_fresh=False,
            last_error="projection integrity failure",
        )

        view = self.assemble(freshness=failure)

        self.assertEqual("failed", view.freshness["state"])
        self.assertFalse(view.decision["submission_allowed"])

    def test_complete_sources_require_each_m2_source_and_remain_independent_of_lag(self) -> None:
        self.catalog.connection.execute(
            "INSERT INTO projects(project_id, locator, created_at) VALUES (?, ?, ?)",
            (self.task.project_id, "file:///m4-fixture", NOW),
        )
        self.catalog.connection.execute(
            "INSERT INTO worktrees(worktree_id, project_id, locator, created_at) VALUES (?, ?, ?, ?)",
            (self.task.worktree_id, self.task.project_id, "file:///m4-fixture/main", NOW),
        )
        self.catalog.connection.execute(
            """
            INSERT INTO tasks(task_id, project_id, worktree_id, mode, commit_hash,
                              branch, cwd, environment_ref, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.task.task_id, self.task.project_id, self.task.worktree_id,
                self.task.mode, self.task.commit, self.task.branch, "/repo",
                self.task.environment_ref, NOW,
            ),
        )
        self.events.append(
            EventDraft(
                event_id="event:complete:task", task_id=self.task.task_id,
                event_type="task.created", event_version=1, occurred_at=NOW,
                payload={"mode": self.task.mode}, collection_method="test",
                redaction_status="not_needed",
            ),
            lambda payload: payload,
        )
        self.store.put(
            EvidenceDraft(
                evidence_id="evidence:direct:human", task_id=self.task.task_id,
                requirement_id="M5-06", evidence_type="direct_feature_probe",
                subject_ref="subject:hwpx", exact_scope="HWPX human observation",
                result="pass", basis="observed",
                fields={"human_observation": True, "adapter": "hwpx"},
                content=b"human observed output", collection_method="human-observation",
                redaction_status="redacted",
            ),
            bytes,
        )
        managed = managed_packet()
        managed["task_id"] = self.task.task_id
        m3 = build_review_packet(
            managed,
            imported_packet(),
            raw_receipt(managed, probe_kind="live"),
            generated_at=NOW,
        )
        guarantee = {
            "report_version": "1.0",
            "task": {
                "project_id": self.task.project_id,
                "worktree_id": self.task.worktree_id,
                "task_id": self.task.task_id,
                "mode": self.task.mode,
                "target_commit": self.task.commit,
                "environment_ref": self.task.environment_ref,
            },
            "claim_results": [{"claim_id": "GM-016", "verdict": "supported"}],
        }
        stale = replace(
            self.freshness,
            event_head=3,
            projected_sequence=2,
            is_fresh=False,
        )
        projection = replace(self.projection, projected_sequence=2)
        common = {
            "freshness": stale,
            "projection": projection,
            "baseline": {"baseline_id": "baseline:1", "fingerprint": "sha256:" + "1" * 64},
            "context_status": {"status_id": "context:1", "fingerprint": "sha256:" + "2" * 64},
            "m3_packet": m3,
            "guarantee_report": guarantee,
        }

        complete = self.assemble(**common)
        missing_baseline = self.assemble(**{**common, "baseline": None})

        self.assertEqual("stale", complete.freshness["state"])
        self.assertEqual("complete", complete.completeness["state"])
        self.assertEqual("unobserved", missing_baseline.completeness["state"])
        self.assertIn("project_baseline", missing_baseline.completeness["missing"])
        self.assertFalse(complete.decision["submission_allowed"])

        direct = self.store.resolve("evidence:direct:human")
        direct.object_path.write_bytes(b"tampered human observation")
        tampered_direct = self.assemble(**common)
        self.assertEqual("unobserved", tampered_direct.completeness["state"])
        self.assertIn("human_feature_observation", tampered_direct.completeness["missing"])


if __name__ == "__main__":
    unittest.main()

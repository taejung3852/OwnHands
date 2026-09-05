from __future__ import annotations

import unittest
import copy
import json
from dataclasses import replace
from pathlib import Path

from devharness.assurance import fingerprint
from devharness.evidence import EvidenceDraft
from devharness.events import EventDraft
from devharness.guarantees import GuaranteeEvaluator
from devharness.m3_review import build_review_packet
from tests import test_dashboard_view as dashboard_view_fixtures
from tests.test_m3_review import imported_packet, managed_packet, raw_receipt


NOW = dashboard_view_fixtures.NOW
MATRIX = Path(__file__).resolve().parents[1] / "docs/product/guarantee-matrix.v1.json"
CONTEXT_EXAMPLE = (
    Path(__file__).resolve().parents[1] / "docs/product/context-status-report.example.json"
)


def canonical_baseline(task) -> dict:
    baseline = {
        "baseline_version": "1.0",
        "baseline_id": f"baseline:{task.project_id}:v1",
        "version": 1,
        "predecessor_ref": None,
        "project_id": task.project_id,
        "worktree_id": task.worktree_id,
        "environment_ref": task.environment_ref,
        "profile_ref": "sha256:" + "1" * 64,
        "interview_ref": "sha256:" + "2" * 64,
        "source_fingerprints": {},
        "sources": [],
        "commands": [],
        "sensitive_paths": [],
        "external_services": [],
        "hwpx_tool_contract": {
            "basis": "unobserved",
            "tools": [],
            "reason": "no supported HWPX tool contract",
        },
        "unobserved": [],
        "event_refs": [],
        "evidence_refs": [],
    }
    baseline["fingerprint"] = fingerprint(baseline)
    return baseline


def canonical_context_status() -> dict:
    return json.loads(CONTEXT_EXAMPLE.read_text(encoding="utf-8"))


class DashboardFreshnessTests(unittest.TestCase):
    setUp = dashboard_view_fixtures.DashboardViewTests.setUp
    tearDown = dashboard_view_fixtures.DashboardViewTests.tearDown
    assemble = dashboard_view_fixtures.DashboardViewTests.assemble

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

    def test_freshness_requires_projection_status_sequence_to_close_too(self) -> None:
        inconsistent_projection = replace(self.projection, projected_sequence=1)

        view = self.assemble(projection=inconsistent_projection)

        self.assertEqual("stale", view.freshness["state"])
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
                subject_ref="subject:hwpx:document", exact_scope="HWPX human observation",
                result="pass", basis="observed",
                fields={
                    "adapter": "hwpx",
                    "input": "source:document",
                    "expected": "expected:render",
                    "actual": "actual:render",
                    "environment": self.task.environment_ref,
                    "generated_files": ["artifact:rendered-document"],
                    "human_observation": "human confirmed rendering",
                    "target_commit": self.task.commit,
                    "task_ref": self.task.task_id,
                },
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
        evaluator = GuaranteeEvaluator(self.catalog, self.store, MATRIX)
        guarantee = evaluator.evaluate(self.task.task_id, ["GM-015"])
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
            "baseline": canonical_baseline(self.task),
            "context_status": canonical_context_status(),
            "m3_packet": m3,
            "guarantee_report": guarantee,
            "guarantee_evaluator": evaluator,
        }

        complete = self.assemble(**common)
        missing_baseline = self.assemble(**{**common, "baseline": None})

        self.assertEqual("stale", complete.freshness["state"])
        self.assertEqual("complete", complete.completeness["state"])
        self.assertEqual("unobserved", missing_baseline.completeness["state"])
        self.assertIn("project_baseline", missing_baseline.completeness["missing"])
        self.assertFalse(complete.decision["submission_allowed"])

        forged_report = copy.deepcopy(guarantee)
        forged_report["claim_results"][0]["verdict"] = "supported"
        forged_report["claim_results"][0]["permitted_statement"] = "forged"
        forged = self.assemble(**{**common, "guarantee_report": forged_report})
        self.assertTrue(all(row["status"] == "not_evaluated" for row in forged.guarantees))
        self.assertEqual("unobserved", forged.completeness["state"])

        forged_baseline = {"baseline_id": "baseline:forged", "fingerprint": "sha256:" + "f" * 64}
        forged_context = {"status": "looks-good"}
        forged_m2 = self.assemble(
            **{**common, "baseline": forged_baseline, "context_status": forged_context}
        )
        self.assertEqual("unobserved", forged_m2.completeness["state"])
        self.assertIn("project_baseline", forged_m2.completeness["missing"])
        self.assertIn("context_status", forged_m2.completeness["missing"])
        self.assertEqual("invalid", forged_m2.harness["baseline"]["status"])
        self.assertEqual("invalid", forged_m2.harness["context_status"]["status"])

        malformed_baseline = canonical_baseline(self.task)
        malformed_baseline["hwpx_tool_contract"] = {}
        malformed_baseline["fingerprint"] = fingerprint(
            {key: value for key, value in malformed_baseline.items() if key != "fingerprint"}
        )
        malformed_context = canonical_context_status()
        malformed_context["claim_results"][0]["verdict"] = "supported"
        malformed_context["claim_results"][0]["evidence_refs"] = []
        malformed_context["claim_results"][0]["permitted_statement"] = "forged"
        nested_forgery = self.assemble(
            **{
                **common,
                "baseline": malformed_baseline,
                "context_status": malformed_context,
            }
        )
        self.assertEqual("unobserved", nested_forgery.completeness["state"])
        self.assertIn("project_baseline", nested_forgery.completeness["missing"])
        self.assertIn("context_status", nested_forgery.completeness["missing"])

        malformed_report = copy.deepcopy(guarantee)
        malformed_report.pop("generated_at")
        malformed = self.assemble(**{**common, "guarantee_report": malformed_report})
        self.assertTrue(all(row["status"] == "not_evaluated" for row in malformed.guarantees))
        self.assertEqual("unobserved", malformed.completeness["state"])

        stale_report = copy.deepcopy(guarantee)
        stale_report["task"]["target_commit"] = "stale-commit"
        stale_report_view = self.assemble(**{**common, "guarantee_report": stale_report})
        self.assertTrue(all(row["status"] == "not_evaluated" for row in stale_report_view.guarantees))
        self.assertEqual("unobserved", stale_report_view.completeness["state"])

        direct = self.store.resolve("evidence:direct:human")
        direct.object_path.write_bytes(b"tampered human observation")
        tampered_direct = self.assemble(**common)
        self.assertEqual("unobserved", tampered_direct.completeness["state"])
        self.assertIn("human_feature_observation", tampered_direct.completeness["missing"])


if __name__ == "__main__":
    unittest.main()

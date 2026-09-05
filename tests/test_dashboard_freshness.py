from __future__ import annotations

import unittest
import copy
import json
import inspect
from dataclasses import asdict, replace
from pathlib import Path

from devharness.assurance import canonical_json, fingerprint
from devharness.context_architecture import evaluate_context_guarantees, validate_manifest, validate_status_report
from devharness.control_profile import build_baseline, run_interview
from devharness.evidence import EvidenceDraft
from devharness.events import EventDraft
from devharness.guarantees import GuaranteeEvaluator
from devharness.dashboard_view import assemble_task_review
from devharness.identity import IdentityRegistry
from devharness.m3_review import build_review_packet
from tests import test_dashboard_view as dashboard_view_fixtures
from tests.test_m3_review import imported_packet, managed_packet, raw_receipt
from tests.test_context_architecture import manifest as context_manifest


NOW = dashboard_view_fixtures.NOW
MATRIX = Path(__file__).resolve().parents[1] / "docs/product/guarantee-matrix.v1.json"
CONTEXT_EXAMPLE = (
    Path(__file__).resolve().parents[1] / "docs/product/context-status-report.example.json"
)


def canonical_baseline(task) -> dict:
    profile = {
        "profile_version": "1.0",
        "project_id": task.project_id,
        "worktree_id": task.worktree_id,
        "environment_ref": task.environment_ref,
        "observed_at": NOW,
        "structure": [],
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
    }
    profile["fingerprint"] = fingerprint(profile)
    interview = run_interview(profile, ["low", "tests"])
    return build_baseline(profile, interview, version=1, predecessor_ref=None, event_refs=[], evidence_refs=[])


def canonical_context_status() -> dict:
    return json.loads(CONTEXT_EXAMPLE.read_text(encoding="utf-8"))


def register_artifact(store, task, kind: str, artifact: dict):
    reference = artifact["baseline_id" if kind == "project_baseline" else "manifest_ref"]
    return store.put(
        EvidenceDraft(
            evidence_id="evidence:m2:" + kind + ":" + fingerprint(artifact)[7:],
            task_id=task.task_id, requirement_id="M5-05", evidence_type="active_configuration",
            subject_ref=reference, exact_scope="validated M2 artifact for this Task",
            result="pass", basis="observed",
            fields={"artifact_kind": kind, "artifact_ref": reference,
                    "artifact_fingerprint": fingerprint(artifact),
                    "environment": task.environment_ref, "target_commit": task.commit},
            content=canonical_json(artifact).encode("utf-8"),
            collection_method="m2-validated-artifact", redaction_status="redacted",
        ), bytes,
    )


def registered_context(store, task) -> dict:
    manifest = context_manifest()
    manifest["task"] = {
        "project_id": task.project_id, "worktree_id": task.worktree_id,
        "task_id": task.task_id, "mode": task.mode, "target_commit": task.commit,
        "cwd": task.cwd, "environment_ref": task.environment_ref,
    }
    manifest["event_refs"] = [store.events.list_for_task(task.task_id)[0].event_id]
    records = []
    for reference in manifest["evidence_refs"]:
        records.append(store.put(
            EvidenceDraft(
                evidence_id=reference, task_id=task.task_id, requirement_id="M5-05",
                evidence_type="instruction_loading" if reference == "ev-loaded" else "active_configuration",
                subject_ref="ctx-agents", exact_scope="fixture manifest sources",
                result="pass", basis="observed",
                fields={"manifest_ref": manifest["manifest_id"], "task_ref": task.task_id,
                        "source_refs": ["ctx-agents", "ctl-sandbox"],
                        "environment": task.environment_ref, "target_commit": task.commit},
                content=reference.encode(), collection_method="m2-fixture-observation",
                redaction_status="redacted",
            ), bytes,
        ))
    validate_manifest(manifest, {record.evidence_id for record in records}, set(manifest["event_refs"]))
    matrix = json.loads((MATRIX.parent / "context-guarantee-matrix.proposed.json").read_text())
    documents = [asdict(record) for record in records]
    report = {
        "report_version": "1.0", "matrix_version": matrix["matrix_version"],
        "manifest_ref": manifest["manifest_id"],
        "active_context": [{"source_ref": "ctx-agents", "evidence_refs": ["ev-loaded"]}],
        "active_controls": [{"source_ref": "ctl-sandbox", "evidence_refs": ["ev-sandbox-probe"]}],
        "excluded_context": [], "applicability_results": [], "lint_findings": [],
        "claim_results": evaluate_context_guarantees(matrix, manifest, documents),
    }
    validate_status_report(report, manifest, matrix, documents)
    register_artifact(store, task, "context_status", report)
    return report


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

    def register_task(self) -> None:
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

    def test_original_assembler_arguments_validate_authoritative_guarantee(self) -> None:
        self.register_task()
        evaluator = GuaranteeEvaluator(self.catalog, self.store, MATRIX)
        report = evaluator.evaluate(self.task.task_id, ["GM-015"])

        view = self.assemble(guarantee_report=report)

        self.assertNotIn("task_guarantee_report", view.completeness["missing"])
        self.assertEqual("not_evaluated", view.guarantees[0]["status"])
        self.assertEqual(
            {"task", "events", "projection", "freshness", "evidence_store", "baseline",
             "context_status", "execution_contract", "m3_packet", "assurance_packet",
             "guarantee_report", "assembled_at"},
            set(inspect.signature(assemble_task_review).parameters),
        )

    def complete_sources(self) -> dict:
        baseline = canonical_baseline(self.task)
        root = Path(self.temporary.name) / "bound-m4"
        root.mkdir()
        self.packet, execution_contract = dashboard_view_fixtures.bound_packet(
            root, baseline, with_relations=True,
            task={"project_id": self.task.project_id, "worktree_id": self.task.worktree_id,
                  "task_id": self.task.task_id, "environment_ref": self.task.environment_ref,
                  "mode": self.task.mode, "goal": "verify source closure"},
        )
        self.task = replace(self.task, commit=self.packet["restore_point"]["start_commit"])
        self.register_task()
        register_artifact(self.store, self.task, "project_baseline", baseline)
        context = registered_context(self.store, self.task)
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
            event_head=self.events.head_sequence(self.task.task_id),
            projected_sequence=self.events.head_sequence(self.task.task_id) - 1,
            is_fresh=False,
        )
        projection = replace(self.projection, projected_sequence=stale.projected_sequence)
        return {
            "freshness": stale,
            "projection": projection,
            "baseline": baseline,
            "context_status": context,
            "execution_contract": execution_contract,
            "m3_packet": m3,
            "guarantee_report": guarantee,
        }

    def test_registered_baseline_rejects_substitution_and_missing_registration(self) -> None:
        common = self.complete_sources()
        self.assertEqual("complete", self.assemble(**common).completeness["state"])
        substituted = copy.deepcopy(common["baseline"])
        substituted["interview_ref"] = "sha256:" + "f" * 64
        substituted["fingerprint"] = fingerprint({k: v for k, v in substituted.items() if k != "fingerprint"})
        view = self.assemble(**{**common, "baseline": substituted})
        self.assertIn("project_baseline", view.completeness["missing"])
        self.assertNotEqual("observed", view.harness["baseline"]["status"])
        registration = next(r for r in self.store.list_for_task(self.task.task_id)
                            if r.fields.get("artifact_kind") == "project_baseline")
        self.store.purge(registration.evidence_id, "test missing registration")
        missing = self.assemble(**common)
        self.assertIn("project_baseline", missing.completeness["missing"])
        self.assertEqual("unobserved", missing.diagram["state"])

    def test_relationless_diagram_has_a_fully_bound_positive_control(self) -> None:
        common = self.complete_sources()
        with_relations = self.assemble(**common)
        self.assertEqual("observed", with_relations.diagram["state"])
        self.assertTrue(with_relations.diagram["edges"])
        root = Path(self.temporary.name) / "bound-m4"
        packet, contract = dashboard_view_fixtures.bound_packet(
            root, common["baseline"], with_relations=False,
            task=common["execution_contract"]["task"], repository=root / "repository",
        )
        view = self.assemble(**{**common, "execution_contract": contract, "assurance_packet": packet})
        self.assertEqual("closed", view.assurance["source"]["status"])
        self.assertEqual("closed", view.summary["contract"]["status"])
        self.assertEqual("observed", view.harness["baseline"]["status"])
        self.assertEqual(common["baseline"]["fingerprint"], contract["baseline_fingerprint"])
        self.assertTrue(contract["assurance_draft"]["impact_hypotheses"])
        self.assertEqual([], packet["impact"]["relations"])
        self.assertEqual("unobserved", view.diagram["state"])
        self.assertEqual((), view.diagram["nodes"])
        self.assertEqual((), view.diagram["edges"])

    def test_registered_context_requires_resolved_support(self) -> None:
        common = self.complete_sources()
        self.assertEqual("complete", self.assemble(**common).completeness["state"])
        self.store.purge("ev-loaded", "test dangling Context support")
        view = self.assemble(**common)
        self.assertIn("context_status", view.completeness["missing"])
        self.assertNotEqual("observed", view.harness["context_status"]["status"])

    def test_registered_sources_remain_deterministic_without_writes(self) -> None:
        common = self.complete_sources()
        before_changes = self.catalog.connection.total_changes
        before_files = {path.relative_to(self.catalog.paths.root): path.read_bytes()
                        for path in self.catalog.paths.root.rglob("*") if path.is_file()}
        first = self.assemble(**common)
        second = self.assemble(**common)
        self.assertEqual("complete", first.completeness["state"])
        self.assertEqual(first, second)
        self.assertEqual(before_changes, self.catalog.connection.total_changes)
        self.assertEqual(before_files, {path.relative_to(self.catalog.paths.root): path.read_bytes()
                                      for path in self.catalog.paths.root.rglob("*") if path.is_file()})

    def test_registration_requires_exact_artifact_content(self) -> None:
        common = self.complete_sources()
        registration = next(r for r in self.store.list_for_task(self.task.task_id)
                            if r.fields.get("artifact_kind") == "project_baseline")
        self.store.purge(registration.evidence_id, "replace with metadata-only forgery")
        self.store.put(EvidenceDraft(
            evidence_id="evidence:metadata-only-forgery", task_id=self.task.task_id,
            requirement_id=registration.requirement_id, evidence_type=registration.evidence_type,
            subject_ref=registration.subject_ref, exact_scope=registration.exact_scope,
            result=registration.result, basis=registration.basis, fields=registration.fields,
            content=b"not the registered baseline", collection_method=registration.collection_method,
            redaction_status=registration.redaction_status,
        ), bytes)
        view = self.assemble(**common)
        self.assertIn("project_baseline", view.completeness["missing"])
        self.assertEqual("unobserved", view.harness["baseline"]["status"])

    def test_explicit_event_and_nested_conflict_references_must_resolve(self) -> None:
        common = self.complete_sources()
        baseline = copy.deepcopy(common["baseline"])
        baseline["event_refs"] = ["event:unregistered"]
        baseline["fingerprint"] = fingerprint({k: v for k, v in baseline.items() if k != "fingerprint"})
        register_artifact(self.store, self.task, "project_baseline", baseline)
        root = Path(self.temporary.name) / "bound-m4"
        packet, contract = dashboard_view_fixtures.bound_packet(
            root, baseline, with_relations=True, task=common["execution_contract"]["task"],
            repository=root / "repository",
        )
        view = self.assemble(**{**common, "baseline": baseline, "assurance_packet": packet, "execution_contract": contract})
        self.assertIn("project_baseline", view.completeness["missing"])
        report = copy.deepcopy(common["context_status"])
        report["claim_results"][0]["conflict_refs"] = ["evidence:unregistered-conflict"]
        register_artifact(self.store, self.task, "context_status", report)
        view = self.assemble(**{**common, "context_status": report})
        self.assertIn("context_status", view.completeness["missing"])

    def test_registered_context_rejects_foreign_and_unbound_support(self) -> None:
        common = self.complete_sources()
        self.assertEqual("complete", self.assemble(**common).completeness["state"])
        foreign = IdentityRegistry(self.catalog).create_task(
            self.task.worktree_id, self.task.mode, self.task.commit,
            self.task.branch, self.task.cwd, self.task.environment_ref,
        )
        self.events.append(EventDraft(
            event_id="event:foreign:created", task_id=foreign.task_id,
            event_type="task.created", event_version=1, occurred_at=NOW,
            payload={"mode": foreign.mode}, collection_method="test", redaction_status="not_needed",
        ), lambda value: value)
        for attack in ("missing", "foreign", "manifest", "source", "bytes"):
            with self.subTest(attack=attack):
                reference = "evidence:context:" + attack
                if attack != "missing":
                    record = self.store.put(EvidenceDraft(
                        evidence_id=reference,
                        task_id=foreign.task_id if attack == "foreign" else self.task.task_id,
                        requirement_id="M5-05", evidence_type="instruction_loading",
                        subject_ref="ctx-agents", exact_scope="context attack",
                        result="pass", basis="observed",
                        fields={"manifest_ref": "other-manifest" if attack == "manifest" else common["context_status"]["manifest_ref"],
                                "task_ref": self.task.task_id,
                                "source_ref": "other-source" if attack == "source" else "ctx-agents"},
                        content=reference.encode(), collection_method="test-attack",
                        redaction_status="redacted",
                    ), bytes)
                    if attack == "bytes":
                        record.object_path.write_bytes(b"tampered context support")
                report = copy.deepcopy(common["context_status"])
                report["active_context"][0]["evidence_refs"] = [reference]
                register_artifact(self.store, self.task, "context_status", report)
                view = self.assemble(**{**common, "context_status": report})
                self.assertIn("context_status", view.completeness["missing"])
                self.assertNotEqual("observed", view.harness["context_status"]["status"])

    def test_complete_sources_require_each_m2_source_and_remain_independent_of_lag(self) -> None:
        common = self.complete_sources()
        guarantee = common["guarantee_report"]
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

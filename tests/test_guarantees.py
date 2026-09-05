from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from devharness.catalog import Catalog
from devharness.evidence import EVIDENCE_TYPES, EvidenceDraft, EvidenceStore
from devharness.events import EventDraft, EventLog
from devharness.guarantees import (
    CATEGORIES,
    GuaranteeEvaluator,
    GuaranteeValidationError,
)
from devharness.identity import IdentityRegistry
from devharness.paths import DataPaths
from devharness.projections import PROJECTION_VERSION, ProjectionEngine


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPOSITORY_ROOT / "docs/product/guarantee-matrix.v1.json"
ATTACKS_PATH = Path(__file__).parent / "fixtures/guarantee_attacks.json"


def identity_bytes(content: bytes) -> bytes:
    return content


class GuaranteeEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.paths = DataPaths.resolve(Path(self.temporary_directory.name) / "data")
        self.catalog = Catalog.open(self.paths)
        self.registry = IdentityRegistry(self.catalog)
        project = self.registry.register_project("file:///repo")
        worktree = self.registry.register_worktree(project.project_id, "file:///repo/main")
        self.managed = self.registry.create_task(
            worktree.worktree_id,
            mode="managed",
            commit="abc123",
            branch="main",
            cwd="/repo/main",
            environment_ref="local-test",
        )
        self.imported = self.registry.create_task(
            worktree.worktree_id,
            mode="imported",
            commit="abc123",
            branch="main",
            cwd="/repo/main",
            environment_ref="local-test",
        )
        self.events = EventLog(self.catalog)
        for event_id, task, mode in (
            ("task-created:managed-guarantee-tests", self.managed, "managed"),
            ("task-created:imported-guarantee-tests", self.imported, "imported"),
        ):
            self.events.append(
                EventDraft(
                    event_id=event_id,
                    task_id=task.task_id,
                    event_type="task.created",
                    event_version=1,
                    occurred_at="2026-09-04T11:59:59+00:00",
                    payload={"mode": mode},
                    collection_method="guarantee-test",
                    redaction_status="not_needed",
                ),
                lambda payload: payload,
            )
        self.store = EvidenceStore(self.catalog, self.events)
        self.evaluator = GuaranteeEvaluator(self.catalog, self.store, MATRIX_PATH)

    def tearDown(self) -> None:
        self.catalog.close()
        self.temporary_directory.cleanup()

    def add_test_evidence(
        self,
        *,
        task_id: str | None = None,
        evidence_id: str = "evidence-test-pass",
        result: str = "pass",
        basis: str = "observed",
        fields: dict | None = None,
        conflict_refs: tuple[str, ...] = (),
    ):
        return self.store.put(
            EvidenceDraft(
                evidence_id=evidence_id,
                task_id=task_id or self.managed.task_id,
                requirement_id="test-run",
                evidence_type="test_execution",
                subject_ref="test-selection.synthetic",
                exact_scope="tests/hwpx-package",
                result=result,
                basis=basis,
                fields=fields
                or {
                    "command": "python -m unittest tests.hwpx",
                    "environment": "local-test",
                    "target_commit": "abc123",
                    "selection_scope": "HWPX package inspection",
                    "result": result,
                },
                content=f"test result: {result}".encode(),
                collection_method="synthetic-fixture",
                redaction_status="not_needed",
                inference_from=("evidence-observed-input",) if basis == "inferred" else (),
                conflict_refs=conflict_refs,
            ),
            identity_bytes,
        )

    def add_profile_evidence(self, evidence_id: str = "evidence-profile"):
        return self.store.put(
            EvidenceDraft(
                evidence_id=evidence_id,
                task_id=self.managed.task_id,
                requirement_id="profile-artifact",
                evidence_type="file_creation",
                subject_ref="config.synthetic-profile",
                exact_scope="config/profile.json",
                result="pass",
                basis="observed",
                fields={
                    "file_hash": "sha256:abc",
                    "diff": "created config/profile.json",
                    "parse_result": "pass",
                },
                content=b"synthetic profile",
                collection_method="synthetic-fixture",
                redaction_status="not_needed",
            ),
            identity_bytes,
        )

    def control_record(
        self,
        *,
        record_id: str = "control-profile-pass",
        control_id: str = "config.synthetic-profile",
        boundary: str = "config/profile.json",
        configured_result: str = "pass",
    ) -> dict:
        configured_basis = "observed" if configured_result in {"pass", "fail"} else "unobserved"
        return {
            "schema_version": "1.0",
            "record_id": record_id,
            "control_id": control_id,
            "control_type": "control_profile",
            "scope": {
                "project_id": self.managed.project_id,
                "worktree_id": self.managed.worktree_id,
                "task_id": self.managed.task_id,
                "boundary": boundary,
                "environment_ref": self.managed.environment_ref,
            },
            "checks": {
                "configured": {
                    "result": configured_result,
                    "basis": configured_basis,
                    "evidence_refs": ["evidence-profile"] if configured_basis == "observed" else [],
                    "inference_from": [],
                    "checked_at": "2026-09-04T12:00:00+00:00" if configured_basis == "observed" else None,
                    "exact_scope": boundary if configured_basis == "observed" else "",
                    "residual_risks": ["current runtime loading is not evaluated"],
                },
                "loaded": {
                    "result": "not_run",
                    "basis": "unobserved",
                    "evidence_refs": [],
                    "inference_from": [],
                    "checked_at": None,
                    "exact_scope": "",
                    "residual_risks": ["not observed"],
                },
                "enforced": {
                    "result": "not_run",
                    "basis": "unobserved",
                    "evidence_refs": [],
                    "inference_from": [],
                    "checked_at": None,
                    "exact_scope": "",
                    "residual_risks": ["not observed"],
                },
            },
        }

    def test_supported_claim_comes_from_authoritative_evidence(self) -> None:
        evidence = self.add_test_evidence()

        report = self.evaluator.evaluate(self.managed.task_id, ["GM-013"])
        result = report["claim_results"][0]

        self.assertEqual("supported", result["verdict"])
        self.assertEqual("관련 테스트를 실행했다", result["permitted_statement"])
        self.assertEqual([evidence.evidence_id], result["requirement_results"][0]["evidence_refs"])
        self.assertEqual(
            ["선택되지 않은 테스트와 실환경 차이"], result["residual_risks"]
        )

    def test_imported_managed_only_claim_is_not_evaluated(self) -> None:
        report = self.evaluator.evaluate(self.imported.task_id, ["GM-002"])

        self.assertEqual("not_evaluated", report["claim_results"][0]["verdict"])
        self.assertIsNone(report["claim_results"][0]["permitted_statement"])

    def test_hook_is_evidence_not_an_invented_control_type(self) -> None:
        self.store.put(
            EvidenceDraft(
                evidence_id="evidence-hook",
                task_id=self.managed.task_id,
                requirement_id="hook-receipt",
                evidence_type="hook_execution",
                subject_ref="hook.after-agent",
                exact_scope="after-agent lifecycle",
                result="pass",
                basis="observed",
                fields={
                    "event_type": "after-agent",
                    "started_or_handler_receipt": "receipt-1",
                    "completed_or_handler_result": "completed",
                    "runtime_version": "synthetic-1",
                },
                content=b"synthetic hook receipt",
                collection_method="synthetic-fixture",
                redaction_status="not_needed",
            ),
            identity_bytes,
        )

        report = self.evaluator.evaluate(self.managed.task_id, ["GM-005"])

        self.assertEqual("supported", report["claim_results"][0]["verdict"])
        invalid_control = self.control_record()
        invalid_control["control_type"] = "hook"
        with self.assertRaisesRegex(GuaranteeValidationError, "control_type"):
            self.evaluator.record_control_validation(self.managed.task_id, invalid_control)

    def test_observed_evidence_failure_is_contradicted(self) -> None:
        self.add_test_evidence(result="fail")

        result = self.evaluator.evaluate(self.managed.task_id, ["GM-013"])[
            "claim_results"
        ][0]

        self.assertEqual("contradicted", result["verdict"])
        self.assertEqual(["evidence-test-pass"], result["conflict_refs"])

    def test_missing_field_inferred_basis_and_tampered_object_are_not_supported(self) -> None:
        incomplete_fields = {
            "command": "python -m unittest tests.hwpx",
            "environment": "synthetic-local",
            "target_commit": "abc123",
            "result": "pass",
        }
        self.add_test_evidence(fields=incomplete_fields)
        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(self.managed.task_id, ["GM-013"])[
                "claim_results"
            ][0]["verdict"],
        )

        other_task = self.imported.task_id
        inferred = self.add_test_evidence(
            task_id=other_task,
            evidence_id="evidence-inferred",
            basis="inferred",
        )
        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(other_task, ["GM-013"])["claim_results"][0][
                "verdict"
            ],
        )
        inferred.object_path.write_bytes(b"tampered")
        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(other_task, ["GM-013"])["claim_results"][0][
                "verdict"
            ],
        )

    def test_tampering_downgrades_previously_supported_observed_evidence(self) -> None:
        evidence = self.add_test_evidence()
        self.assertEqual(
            "supported",
            self.evaluator.evaluate(self.managed.task_id, ["GM-013"])[
                "claim_results"
            ][0]["verdict"],
        )

        evidence.object_path.write_bytes(b"tampered")

        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(self.managed.task_id, ["GM-013"])[
                "claim_results"
            ][0]["verdict"],
        )

    def test_catalog_tampering_cannot_turn_fail_into_supported(self) -> None:
        evidence = self.add_test_evidence(result="fail")
        self.assertEqual(
            "contradicted",
            self.evaluator.evaluate(self.managed.task_id, ["GM-013"])[
                "claim_results"
            ][0]["verdict"],
        )
        self.catalog.connection.execute(
            "DROP TRIGGER evidence_canonical_fields_immutable"
        )
        self.catalog.connection.execute(
            "UPDATE evidence SET result='pass' WHERE evidence_id=?",
            (evidence.evidence_id,),
        )

        with self.assertRaisesRegex(GuaranteeValidationError, "integrity"):
            self.evaluator.evaluate(self.managed.task_id, ["GM-013"])

    def test_explicit_evidence_conflict_is_contradicted(self) -> None:
        self.add_test_evidence(conflict_refs=("declared-conflict",))

        result = self.evaluator.evaluate(self.managed.task_id, ["GM-013"])[
            "claim_results"
        ][0]

        self.assertEqual("contradicted", result["verdict"])
        self.assertIn("declared-conflict", result["conflict_refs"])

    def test_inferred_evidence_requires_an_observed_source_record(self) -> None:
        def add_inferred(evidence_id: str, source_id: str):
            return self.store.put(
                EvidenceDraft(
                    evidence_id=evidence_id,
                    task_id=self.managed.task_id,
                    requirement_id="impact-analysis",
                    evidence_type="feature_impact",
                    subject_ref="feature.synthetic",
                    exact_scope="src/devharness",
                    result="pass",
                    basis="inferred",
                    fields={
                        "analysis_scope": "src/devharness",
                        "dependency_data_or_trace": "synthetic dependency trace",
                        "basis": "inferred",
                        "unobserved_paths": "runtime plugins",
                    },
                    content=b"synthetic inferred impact analysis",
                    collection_method="synthetic-fixture",
                    redaction_status="not_needed",
                    inference_from=(source_id,),
                ),
                identity_bytes,
            )

        missing_source = add_inferred("inferred-with-missing-source", "does-not-exist")
        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(self.managed.task_id, ["GM-012"])[
                "claim_results"
            ][0]["verdict"],
        )
        self.store.purge(missing_source.evidence_id, "test isolation")

        source = self.store.put(
            EvidenceDraft(
                evidence_id="observed-impact-source",
                task_id=self.managed.task_id,
                requirement_id="impact-source",
                evidence_type="workspace_diff",
                subject_ref="task:synthetic:diff",
                exact_scope="src/devharness",
                result="pass",
                basis="observed",
                fields={"diff_summary": "three files changed"},
                content=b"synthetic observed workspace diff",
                collection_method="synthetic-fixture",
                redaction_status="not_needed",
            ),
            identity_bytes,
        )
        add_inferred("inferred-with-observed-source", source.evidence_id)

        result = self.evaluator.evaluate(self.managed.task_id, ["GM-012"])[
            "claim_results"
        ][0]
        self.assertEqual("supported", result["verdict"])
        self.assertEqual([source.evidence_id], result["requirement_results"][0]["inference_from"])

    def test_required_evidence_fields_bind_to_task_and_record(self) -> None:
        mutations = {
            "target_commit": {
                "command": "python -m unittest tests.hwpx",
                "environment": "local-test",
                "target_commit": "FOREIGN",
                "selection_scope": "HWPX package inspection",
                "result": "pass",
            },
            "environment": {
                "command": "python -m unittest tests.hwpx",
                "environment": "FOREIGN",
                "target_commit": "abc123",
                "selection_scope": "HWPX package inspection",
                "result": "pass",
            },
            "result": {
                "command": "python -m unittest tests.hwpx",
                "environment": "local-test",
                "target_commit": "abc123",
                "selection_scope": "HWPX package inspection",
                "result": "fail",
            },
            "numeric material": {
                "command": 1,
                "environment": 2,
                "target_commit": 3,
                "selection_scope": 4,
                "result": 5,
            },
        }
        for index, (name, fields) in enumerate(mutations.items(), start=1):
            with self.subTest(mutation=name):
                self.add_test_evidence(
                    task_id=self.managed.task_id,
                    evidence_id=f"semantic-{index}",
                    fields=fields,
                )
                result = self.evaluator.evaluate(self.managed.task_id, ["GM-013"])[
                    "claim_results"
                ][0]
                self.assertNotEqual("supported", result["verdict"])
                self.store.purge(f"semantic-{index}", "test isolation")

    def test_control_instance_scope_and_all_records_are_evaluated(self) -> None:
        self.add_profile_evidence()
        self.evaluator.record_control_validation(
            self.managed.task_id, self.control_record()
        )
        self.assertEqual(
            "supported",
            self.evaluator.evaluate(self.managed.task_id, ["GM-001"])[
                "claim_results"
            ][0]["verdict"],
        )

        self.evaluator.record_control_validation(
            self.managed.task_id,
            self.control_record(
                record_id="control-profile-fail", configured_result="fail"
            ),
        )
        result = self.evaluator.evaluate(self.managed.task_id, ["GM-001"])[
            "claim_results"
        ][0]
        self.assertEqual("contradicted", result["verdict"])
        self.assertCountEqual(
            ["control-profile-pass", "control-profile-fail"],
            result["control_validation_refs"],
        )

    def test_unrelated_evidence_cannot_close_an_observed_control_check(self) -> None:
        self.add_profile_evidence()
        unrelated = self.add_test_evidence()
        record = self.control_record()
        record["checks"]["configured"]["evidence_refs"] = [unrelated.evidence_id]
        self.evaluator.record_control_validation(self.managed.task_id, record)

        result = self.evaluator.evaluate(self.managed.task_id, ["GM-001"])[
            "claim_results"
        ][0]

        self.assertEqual("not_evaluated", result["verdict"])

    def test_control_validation_is_immutable_and_fingerprint_checked(self) -> None:
        self.add_profile_evidence()
        record = self.control_record()
        self.evaluator.record_control_validation(self.managed.task_id, record)

        with self.assertRaisesRegex(sqlite3.DatabaseError, "immutable"):
            self.catalog.connection.execute(
                "UPDATE control_validations SET record_json='{}' WHERE record_id=?",
                (record["record_id"],),
            )

        self.catalog.connection.execute("DROP TRIGGER control_validations_no_update")
        self.catalog.connection.execute(
            "UPDATE control_validations SET record_json='{}' WHERE record_id=?",
            (record["record_id"],),
        )
        with self.assertRaisesRegex(GuaranteeValidationError, "integrity"):
            self.evaluator.evaluate(self.managed.task_id, ["GM-001"])

    def test_different_control_instance_cannot_support(self) -> None:
        self.add_profile_evidence()
        self.evaluator.record_control_validation(
            self.managed.task_id,
            self.control_record(control_id="config.other-profile"),
        )
        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(self.managed.task_id, ["GM-001"])[
                "claim_results"
            ][0]["verdict"],
        )

    def test_different_control_boundary_cannot_support(self) -> None:
        self.add_profile_evidence()
        wrong_boundary = self.control_record(
            record_id="control-wrong-boundary", boundary="config/other.json"
        )
        self.evaluator.record_control_validation(self.managed.task_id, wrong_boundary)
        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(self.managed.task_id, ["GM-001"])[
                "claim_results"
            ][0]["verdict"],
        )

    def test_each_control_task_scope_field_is_checked_independently(self) -> None:
        self.add_profile_evidence()
        scope_fields = ("project_id", "worktree_id", "task_id", "environment_ref")
        executed_mutations = []
        for field in scope_fields:
            record = self.control_record(record_id=f"control-wrong-{field}")
            record["scope"][field] = f"other-{field}"
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    GuaranteeValidationError, "control task scope mismatch"
                ):
                    self.evaluator.record_control_validation(self.managed.task_id, record)
                executed_mutations.append(field)
        self.assertEqual(len(scope_fields), len(executed_mutations))

    def test_mutated_reports_are_rejected_against_recomputed_result(self) -> None:
        self.add_test_evidence()
        valid = self.evaluator.evaluate(self.managed.task_id, ["GM-013"])
        self.evaluator.validate_report(valid)

        mutations = {}
        empty = copy.deepcopy(valid)
        empty["claim_results"] = []
        mutations["empty claim results"] = empty
        duplicate = copy.deepcopy(valid)
        duplicate["claim_results"].append(copy.deepcopy(duplicate["claim_results"][0]))
        mutations["duplicate claim id"] = duplicate
        conflicting = copy.deepcopy(valid)
        conflicting_result = copy.deepcopy(conflicting["claim_results"][0])
        conflicting_result["verdict"] = "contradicted"
        conflicting_result["permitted_statement"] = None
        conflicting["claim_results"].append(conflicting_result)
        mutations["conflicting verdict for claim"] = conflicting
        unknown_claim = copy.deepcopy(valid)
        unknown_claim["claim_results"][0]["claim_id"] = "GM-999"
        mutations["unknown claim id"] = unknown_claim
        wrong_version = copy.deepcopy(valid)
        wrong_version["matrix_version"] = "999.0"
        mutations["matrix version mismatch"] = wrong_version
        imported_supported = self.evaluator.evaluate(self.imported.task_id, ["GM-002"])
        imported_supported["claim_results"][0]["verdict"] = "supported"
        imported_supported["claim_results"][0]["permitted_statement"] = "특정 config 값이 현재 작업에 로드됐다"
        mutations["imported managed-only supported"] = imported_supported
        missing_requirement = copy.deepcopy(valid)
        missing_requirement["claim_results"][0]["requirement_results"] = []
        mutations["missing requirement id"] = missing_requirement
        extra_requirement = copy.deepcopy(valid)
        extra_requirement["claim_results"][0]["requirement_results"].append(
            copy.deepcopy(extra_requirement["claim_results"][0]["requirement_results"][0])
        )
        extra_requirement["claim_results"][0]["requirement_results"][1][
            "requirement_id"
        ] = "unknown-requirement"
        mutations["extra requirement id"] = extra_requirement
        duplicate_requirement = copy.deepcopy(valid)
        duplicate_requirement["claim_results"][0]["requirement_results"].append(
            copy.deepcopy(duplicate_requirement["claim_results"][0]["requirement_results"][0])
        )
        mutations["duplicate requirement id"] = duplicate_requirement
        verdict_swap = copy.deepcopy(valid)
        verdict_swap["claim_results"][0]["verdict"] = "contradicted"
        verdict_swap["claim_results"][0]["permitted_statement"] = None
        mutations["verdict swap"] = verdict_swap
        unknown_evidence = copy.deepcopy(valid)
        unknown_evidence["claim_results"][0]["requirement_results"][0][
            "evidence_refs"
        ] = ["evidence-does-not-exist"]
        mutations["unknown evidence id"] = unknown_evidence

        for field, name in (
            ("project_id", "project id mismatch"),
            ("worktree_id", "worktree id mismatch"),
            ("task_id", "task id mismatch"),
            ("environment_ref", "environment ref mismatch"),
        ):
            mutation = copy.deepcopy(valid)
            mutation["task"][field] = f"other-{field}"
            mutations[name] = mutation
        wording = copy.deepcopy(valid)
        wording["claim_results"][0]["permitted_statement"] = "다른 문장"
        mutations["canonical claim wording mismatch"] = wording
        scope = copy.deepcopy(valid)
        scope["claim_results"][0]["scope"] = "다른 범위"
        mutations["report scope mismatch"] = scope
        forbidden = copy.deepcopy(valid)
        forbidden["claim_results"][0]["permitted_statement"] = "전체 시스템이 안전하다"
        mutations["global forbidden wording"] = forbidden
        residual = copy.deepcopy(valid)
        residual["claim_results"][0]["residual_risks"] = []
        mutations["required residual risk missing"] = residual
        report_timestamp = copy.deepcopy(valid)
        report_timestamp["generated_at"] = "2026-09-04T00:00:00+00:00"
        mutations["report timestamp detached from claim"] = report_timestamp
        claim_timestamp = copy.deepcopy(valid)
        claim_timestamp["claim_results"][0]["evaluated_at"] = (
            "2026-09-04T00:00:00+00:00"
        )
        mutations["claim timestamp detached from report"] = claim_timestamp

        expected_rejections = {
            attack["name"]
            for attack in json.loads(ATTACKS_PATH.read_text(encoding="utf-8"))
            if attack["probe"]
            == "test_mutated_reports_are_rejected_against_recomputed_result"
        }
        self.assertEqual(expected_rejections, set(mutations))
        executed_rejections = []
        for name, mutation in mutations.items():
            with self.subTest(attack=name):
                with self.assertRaises(GuaranteeValidationError):
                    self.evaluator.validate_report(mutation)
                executed_rejections.append(name)
        self.assertEqual(len(mutations), len(executed_rejections))

    def test_unknown_or_duplicate_claim_request_and_bad_matrix_are_rejected(self) -> None:
        with self.assertRaisesRegex(GuaranteeValidationError, "unknown claim"):
            self.evaluator.evaluate(self.managed.task_id, ["GM-999"])
        with self.assertRaisesRegex(GuaranteeValidationError, "duplicate claim"):
            self.evaluator.evaluate(self.managed.task_id, ["GM-013", "GM-013"])

        matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        matrix["matrix_version"] = "999.0"
        wrong_version_path = Path(self.temporary_directory.name) / "wrong-matrix.json"
        wrong_version_path.write_text(json.dumps(matrix), encoding="utf-8")
        with self.assertRaisesRegex(GuaranteeValidationError, "matrix version"):
            GuaranteeEvaluator(self.catalog, self.store, wrong_version_path)

        forbidden_matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        forbidden_matrix["claims"][0]["claim"] = "전체 시스템이 안전하다"
        forbidden_path = Path(self.temporary_directory.name) / "forbidden-matrix.json"
        forbidden_path.write_text(json.dumps(forbidden_matrix), encoding="utf-8")
        with self.assertRaisesRegex(GuaranteeValidationError, "forbidden wording"):
            GuaranteeEvaluator(self.catalog, self.store, forbidden_path)

        missing_risk_matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        missing_risk_matrix["claims"][0]["residual_risks"] = []
        missing_risk_path = Path(self.temporary_directory.name) / "missing-risk-matrix.json"
        missing_risk_path.write_text(json.dumps(missing_risk_matrix), encoding="utf-8")
        with self.assertRaisesRegex(GuaranteeValidationError, "residual risk"):
            GuaranteeEvaluator(self.catalog, self.store, missing_risk_path)

        invalid_required_fields = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        invalid_required_fields["claims"][12]["required_evidence"][0][
            "required_fields"
        ] = []
        invalid_required_fields_path = (
            Path(self.temporary_directory.name) / "invalid-required-fields-matrix.json"
        )
        invalid_required_fields_path.write_text(
            json.dumps(invalid_required_fields), encoding="utf-8"
        )
        with self.assertRaisesRegex(GuaranteeValidationError, "required_fields"):
            GuaranteeEvaluator(
                self.catalog, self.store, invalid_required_fields_path
            )

    def test_unknown_evidence_type_in_matrix_is_rejected(self) -> None:
        matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        matrix["claims"][12]["required_evidence"][0]["type"] = (
            "invented_magic_evidence"
        )
        matrix_path = Path(self.temporary_directory.name) / "unknown-evidence-type.json"
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

        with self.assertRaisesRegex(GuaranteeValidationError, "unknown Evidence type"):
            GuaranteeEvaluator(self.catalog, self.store, matrix_path)

    def test_matrix_missing_a_required_category_is_rejected_at_runtime(self) -> None:
        matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        missing_category = matrix["claims"].pop()["category"]
        self.assertIn(missing_category, CATEGORIES)
        matrix_path = Path(self.temporary_directory.name) / "missing-category.json"
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

        with self.assertRaisesRegex(GuaranteeValidationError, "categor"):
            GuaranteeEvaluator(self.catalog, self.store, matrix_path)

    def test_matrix_duplicate_category_is_rejected_at_runtime(self) -> None:
        matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        matrix["claims"][1]["category"] = matrix["claims"][0]["category"]
        matrix_path = Path(self.temporary_directory.name) / "duplicate-category.json"
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")

        with self.assertRaisesRegex(GuaranteeValidationError, "categor"):
            GuaranteeEvaluator(self.catalog, self.store, matrix_path)

    def test_runtime_and_matrix_schema_evidence_type_registries_match(self) -> None:
        schema = json.loads(
            (REPOSITORY_ROOT / "docs/product/guarantee-matrix.schema.json").read_text(
                encoding="utf-8"
            )
        )
        schema_types = set(
            schema["$defs"]["claim"]["properties"]["required_evidence"]["items"]
            ["properties"]["type"]["enum"]
        )

        self.assertEqual(EVIDENCE_TYPES, schema_types)

    def test_forbidden_wording_in_evidence_scope_cannot_be_supported(self) -> None:
        self.store.put(
            EvidenceDraft(
                evidence_id="forbidden-scope",
                task_id=self.managed.task_id,
                requirement_id="test-run",
                evidence_type="test_execution",
                subject_ref="test-selection.synthetic",
                exact_scope="전체 시스템이 안전하다",
                result="pass",
                basis="observed",
                fields={
                    "command": "python -m unittest tests.hwpx",
                    "environment": "local-test",
                    "target_commit": "abc123",
                    "selection_scope": "HWPX package inspection",
                    "result": "pass",
                },
                content=b"test result pass",
                collection_method="synthetic-fixture",
                redaction_status="not_needed",
            ),
            identity_bytes,
        )

        report = self.evaluator.evaluate(self.managed.task_id, ["GM-013"])

        self.assertEqual("not_evaluated", report["claim_results"][0]["verdict"])
        self.assertNotIn(
            "전체 시스템이 안전하다", report["claim_results"][0]["scope"]
        )
        self.evaluator.validate_report(report)

    def test_forbidden_wording_is_withheld_from_inapplicable_requirement_scope(self) -> None:
        imported = self.registry.create_task(
            self.imported.worktree_id,
            mode="imported",
            commit="abc123",
            branch="main",
            cwd="/tmp/전체 시스템이 안전하다",
            environment_ref="local-test",
        )

        report = self.evaluator.evaluate(imported.task_id, ["GM-002"])
        result = report["claim_results"][0]

        self.assertEqual("not_evaluated", result["verdict"])
        self.assertNotIn(
            "전체 시스템이 안전하다",
            result["requirement_results"][0]["exact_scope"],
        )
        self.evaluator.validate_report(report)

    def test_dashboard_freshness_claim_requires_actual_projection_state(self) -> None:
        fake = self.store.put(
            EvidenceDraft(
                evidence_id="fake-projection-freshness",
                task_id=self.managed.task_id,
                requirement_id="projection-freshness",
                evidence_type="event_projection_sequence",
                subject_ref=f"task:{self.managed.task_id}:projection",
                exact_scope="task projection",
                result="pass",
                basis="observed",
                fields={
                    "event_head": "999",
                    "projected_sequence": "0",
                    "projection_version": "bogus",
                    "checked_at": "2026-09-04T12:00:00+00:00",
                },
                content=b"fake freshness",
                collection_method="synthetic-fixture",
                redaction_status="not_needed",
            ),
            identity_bytes,
        )
        self.assertEqual(
            "not_evaluated",
            self.evaluator.evaluate(self.managed.task_id, ["GM-016"])[
                "claim_results"
            ][0]["verdict"],
        )
        self.store.purge(fake.evidence_id, "test isolation")

        expected_head = self.events.head_sequence(self.managed.task_id) + 1
        self.store.put(
            EvidenceDraft(
                evidence_id="actual-projection-freshness",
                task_id=self.managed.task_id,
                requirement_id="projection-freshness",
                evidence_type="event_projection_sequence",
                subject_ref=f"task:{self.managed.task_id}:projection",
                exact_scope="task projection",
                result="pass",
                basis="observed",
                fields={
                    "event_head": expected_head,
                    "projected_sequence": expected_head,
                    "projection_version": PROJECTION_VERSION,
                    "checked_at": "2026-09-04T12:00:01+00:00",
                },
                content=b"actual freshness",
                collection_method="synthetic-fixture",
                redaction_status="not_needed",
            ),
            identity_bytes,
        )
        ProjectionEngine(self.catalog, self.events).project(self.managed.task_id)

        self.assertEqual(
            "supported",
            self.evaluator.evaluate(self.managed.task_id, ["GM-016"])[
                "claim_results"
            ][0]["verdict"],
        )

    def test_attack_fixture_names_are_unique_and_expected(self) -> None:
        attacks = json.loads(ATTACKS_PATH.read_text(encoding="utf-8"))
        names = [attack["name"] for attack in attacks]
        probes = [attack["probe"] for attack in attacks]

        self.assertGreater(len(names), 0)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(attack["expected"] in {"rejected", "not_evaluated", "contradicted"} for attack in attacks))
        self.assertTrue(all(probe in dir(self) for probe in probes))


if __name__ == "__main__":
    unittest.main()

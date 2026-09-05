from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .catalog import Catalog
from .evidence import EVIDENCE_TYPES, EvidenceRecord, EvidenceStore
from .events import EventDraft, EventLog
from .identity import IdentityRegistry, TaskIdentity
from .projections import PROJECTION_VERSION, ProjectionEngine


EXPECTED_MATRIX_VERSION = "1.0"
CONTROL_RESULTS = {"pass", "fail", "not_run", "not_applicable"}
CONTROL_BASES = {"observed", "inferred", "unobserved"}
CHECK_NAMES = {"configured", "loaded", "enforced"}
TASK_MODES = {"managed", "imported"}
EVIDENCE_BASES = {"observed", "inferred"}
CONTROL_TYPES = {
    "control_profile",
    "active_config",
    "agents_instruction",
    "rule",
    "sandbox",
    "approval_policy",
}
CATEGORIES = {
    "control_profile_created",
    "config_loaded",
    "agents_instruction_loaded",
    "rule_blocked_probe",
    "hook_invoked_event",
    "sandbox_blocked_boundary",
    "approval_applied_action",
    "config_conflict_identified",
    "mcp_tool_callable",
    "workspace_restore_point_created",
    "actual_changes_identified",
    "related_features_analyzed",
    "related_tests_executed",
    "defined_regression_scope_passed",
    "feature_directly_validated",
    "dashboard_fresh",
}


class GuaranteeValidationError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise GuaranteeValidationError(f"record is not JSON serializable: {error}") from error


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GuaranteeValidationError(f"{name} must be a non-empty string")
    return value


def _material(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bytes):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value) and all(_material(item) for item in value)
    if isinstance(value, dict):
        return bool(value) and all(
            isinstance(key, str) and key.strip() and _material(item)
            for key, item in value.items()
        )
    return False


def _identity_dict(payload: dict) -> dict:
    return payload


class GuaranteeEvaluator:
    def __init__(
        self,
        catalog: Catalog,
        evidence: EvidenceStore,
        matrix_path: Path | str,
    ) -> None:
        self.catalog = catalog
        self.evidence = evidence
        self.events = EventLog(catalog)
        self.projections = ProjectionEngine(catalog, self.events)
        self.identities = IdentityRegistry(catalog)
        self.matrix_path = Path(matrix_path)
        try:
            self.matrix = json.loads(self.matrix_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise GuaranteeValidationError(f"cannot load guarantee matrix: {error}") from error
        self._validate_matrix()
        self.claims = {claim["claim_id"]: claim for claim in self.matrix["claims"]}
        self.allowed_control_types = {
            selector["control_type"]
            for claim in self.matrix["claims"]
            for selector in claim["required_control_selectors"]
        }

    def evaluate(
        self,
        task_id: str,
        claim_ids: list[str] | None = None,
    ) -> dict:
        task = self.identities.get_task(task_id)
        selected_ids = list(self.claims) if claim_ids is None else list(claim_ids)
        if not selected_ids:
            raise GuaranteeValidationError("claim request must not be empty")
        if len(selected_ids) != len(set(selected_ids)):
            raise GuaranteeValidationError("duplicate claim request")
        unknown = [claim_id for claim_id in selected_ids if claim_id not in self.claims]
        if unknown:
            raise GuaranteeValidationError(f"unknown claim: {unknown[0]}")

        evaluated_at = _now()
        try:
            evidence_records = self.evidence.list_for_task(task_id)
        except (OSError, ValueError) as error:
            raise GuaranteeValidationError(
                "authoritative evidence integrity failure"
            ) from error
        control_records = self._list_control_validations(task_id)
        claim_results = [
            self._evaluate_claim(
                task,
                self.claims[claim_id],
                evidence_records,
                control_records,
                evaluated_at,
            )
            for claim_id in selected_ids
        ]
        return {
            "report_version": "1.0",
            "matrix_version": self.matrix["matrix_version"],
            "report_id": str(uuid4()),
            "task": self._task_document(task),
            "generated_at": evaluated_at,
            "claim_results": claim_results,
        }

    def validate_report(self, report: dict) -> None:
        if not isinstance(report, dict):
            raise GuaranteeValidationError("report must be an object")
        expected_top_level = {
            "report_version",
            "matrix_version",
            "report_id",
            "task",
            "generated_at",
            "claim_results",
        }
        if set(report) != expected_top_level:
            raise GuaranteeValidationError("report envelope fields do not match")
        if report["report_version"] != "1.0":
            raise GuaranteeValidationError("report version mismatch")
        if report["matrix_version"] != self.matrix["matrix_version"]:
            raise GuaranteeValidationError("matrix version mismatch")
        _required_text(report["report_id"], "report_id")
        self._validate_timestamp(report["generated_at"], "generated_at")
        if not isinstance(report["task"], dict):
            raise GuaranteeValidationError("task must be an object")
        task_id = _required_text(report["task"].get("task_id"), "task_id")
        try:
            task = self.identities.get_task(task_id)
        except ValueError as error:
            raise GuaranteeValidationError("report task scope mismatch") from error
        if report["task"] != self._task_document(task):
            raise GuaranteeValidationError("report task scope mismatch")

        results = report["claim_results"]
        if not isinstance(results, list) or not results:
            raise GuaranteeValidationError("claim_results must not be empty")
        if not all(isinstance(result, dict) for result in results):
            raise GuaranteeValidationError("claim result must be an object")
        claim_ids = [result.get("claim_id") for result in results]
        if any(not isinstance(claim_id, str) for claim_id in claim_ids):
            raise GuaranteeValidationError("claim_id is required")
        if len(claim_ids) != len(set(claim_ids)):
            raise GuaranteeValidationError("duplicate claim_id or conflicting verdict")
        unknown = [claim_id for claim_id in claim_ids if claim_id not in self.claims]
        if unknown:
            raise GuaranteeValidationError(f"unknown claim: {unknown[0]}")

        for result in results:
            statement = result.get("permitted_statement")
            claim = self.claims[result["claim_id"]]
            if isinstance(statement, str) and self._contains_forbidden(
                statement, claim
            ):
                raise GuaranteeValidationError("global forbidden wording is not permitted")
            if self._contains_forbidden(result.get("scope"), claim):
                raise GuaranteeValidationError(
                    "forbidden wording is not permitted in report scope"
                )
            requirement_results = result.get("requirement_results")
            if isinstance(requirement_results, list) and any(
                isinstance(requirement, dict)
                and self._contains_forbidden(requirement.get("exact_scope"), claim)
                for requirement in requirement_results
            ):
                raise GuaranteeValidationError(
                    "forbidden wording is not permitted in requirement scope"
                )
            self._validate_timestamp(result.get("evaluated_at"), "evaluated_at")
            if result.get("evaluated_at") != report["generated_at"]:
                raise GuaranteeValidationError(
                    "claim evaluated_at must match report generated_at"
                )

        recomputed = self.evaluate(task_id, claim_ids)
        actual_by_claim = {result["claim_id"]: result for result in results}
        expected_by_claim = {
            result["claim_id"]: result for result in recomputed["claim_results"]
        }
        for claim_id in claim_ids:
            actual = copy.deepcopy(actual_by_claim[claim_id])
            expected = copy.deepcopy(expected_by_claim[claim_id])
            actual.pop("evaluated_at", None)
            expected.pop("evaluated_at", None)
            if actual != expected:
                raise GuaranteeValidationError(
                    f"claim result does not match authoritative evaluation: {claim_id}"
                )

    def record_control_validation(self, task_id: str, record: dict) -> None:
        task = self.identities.get_task(task_id)
        self._validate_control_record(task, record)
        document = _canonical_json(record)
        fingerprint = hashlib.sha256(document.encode("utf-8")).hexdigest()
        created_at = _now()
        with self.catalog.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM control_validations WHERE record_id=?",
                (record["record_id"],),
            ).fetchone()
            if existing is not None:
                if existing["fingerprint"] != fingerprint:
                    raise GuaranteeValidationError(
                        "control record_id already has different content"
                    )
                return
            connection.execute(
                """
                INSERT INTO control_validations(
                    record_id, task_id, record_json, fingerprint, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (record["record_id"], task_id, document, fingerprint, created_at),
            )
            self.events.append_in_transaction(
                EventDraft(
                    event_id=f"control-validation-recorded:{record['record_id']}",
                    task_id=task_id,
                    event_type="control.validation.recorded",
                    event_version=1,
                    occurred_at=created_at,
                    payload={
                        "record_id": record["record_id"],
                        "control_id": record["control_id"],
                        "control_type": record["control_type"],
                    },
                    collection_method="control-validation-store",
                    redaction_status="reference_only",
                ),
                _identity_dict,
                connection,
            )

    def _validate_matrix(self) -> None:
        if not isinstance(self.matrix, dict):
            raise GuaranteeValidationError("matrix must be an object")
        if set(self.matrix) != {
            "matrix_version",
            "source",
            "global_forbidden_wording",
            "claims",
        }:
            raise GuaranteeValidationError("matrix fields do not match schema")
        if self.matrix.get("matrix_version") != EXPECTED_MATRIX_VERSION:
            raise GuaranteeValidationError("matrix version mismatch")
        source = self.matrix.get("source")
        if not isinstance(source, dict) or set(source) != {
            "document",
            "section",
            "coverage_rule",
        }:
            raise GuaranteeValidationError("matrix source does not match schema")
        _required_text(source["document"], "matrix source document")
        _required_text(source["section"], "matrix source section")
        if source["coverage_rule"] != "all_documented_core_claim_categories":
            raise GuaranteeValidationError("matrix coverage rule mismatch")
        claims = self.matrix.get("claims")
        if not isinstance(claims, list) or not claims:
            raise GuaranteeValidationError("matrix claims must not be empty")
        self._validate_nonempty_unique_strings(
            self.matrix.get("global_forbidden_wording"),
            "matrix global forbidden wording",
        )
        if not all(isinstance(claim, dict) for claim in claims):
            raise GuaranteeValidationError("matrix claim must be an object")
        claim_ids = [claim.get("claim_id") for claim in claims]
        if any(
            not isinstance(claim_id, str)
            or re.fullmatch(r"GM-[0-9]{3}", claim_id) is None
            for claim_id in claim_ids
        ):
            raise GuaranteeValidationError("matrix claim_id does not match schema")
        if len(claim_ids) != len(set(claim_ids)):
            raise GuaranteeValidationError("matrix duplicate claim_id")
        categories = [claim.get("category") for claim in claims]
        if any(
            not isinstance(category, str) or category not in CATEGORIES
            for category in categories
        ):
            raise GuaranteeValidationError("matrix category is invalid")
        if len(categories) != len(set(categories)):
            raise GuaranteeValidationError("matrix duplicate category")
        if set(categories) != CATEGORIES:
            raise GuaranteeValidationError(
                "matrix categories must match the complete category registry"
            )
        all_requirement_ids: list[str] = []
        for claim in claims:
            required_claim_fields = {
                "claim_id",
                "category",
                "claim",
                "applicable_task_modes",
                "required_realization_checks",
                "required_control_selectors",
                "required_evidence",
                "allowed_basis",
                "evaluation_rule",
                "forbidden_wording",
                "residual_risks",
            }
            if set(claim) != required_claim_fields:
                raise GuaranteeValidationError("matrix claim fields do not match schema")
            if (
                not isinstance(claim["category"], str)
                or claim["category"] not in CATEGORIES
            ):
                raise GuaranteeValidationError("matrix category is invalid")
            _required_text(claim["claim"], "canonical claim")
            self._validate_enum_list(
                claim["applicable_task_modes"], TASK_MODES, "applicable_task_modes"
            )
            self._validate_enum_list(
                claim["required_realization_checks"],
                CHECK_NAMES,
                "required_realization_checks",
                allow_empty=True,
            )
            self._validate_enum_list(
                claim["allowed_basis"], EVIDENCE_BASES, "allowed_basis"
            )
            self._validate_nonempty_unique_strings(
                claim["forbidden_wording"], "forbidden_wording"
            )
            self._validate_nonempty_unique_strings(
                claim["residual_risks"], "matrix required residual risk"
            )
            if claim["evaluation_rule"] != "all_required_pass_without_conflict":
                raise GuaranteeValidationError("matrix evaluation_rule is invalid")
            forbidden = set(self.matrix["global_forbidden_wording"])
            forbidden.update(claim["forbidden_wording"])
            if any(phrase in claim["claim"] for phrase in forbidden):
                raise GuaranteeValidationError(
                    "matrix canonical claim contains forbidden wording"
                )
            requirements = claim["required_evidence"]
            if not isinstance(requirements, list) or not requirements:
                raise GuaranteeValidationError("matrix required_evidence is empty")
            for requirement in requirements:
                if not isinstance(requirement, dict) or set(requirement) != {
                    "requirement_id",
                    "type",
                    "required_fields",
                }:
                    raise GuaranteeValidationError(
                        "matrix Evidence requirement does not match schema"
                    )
                _required_text(requirement["requirement_id"], "requirement_id")
                _required_text(requirement["type"], "Evidence type")
                if requirement["type"] not in EVIDENCE_TYPES:
                    raise GuaranteeValidationError(
                        f"unknown Evidence type: {requirement['type']}"
                    )
                self._validate_nonempty_unique_strings(
                    requirement["required_fields"], "required_fields"
                )
            requirement_ids = [
                requirement["requirement_id"] for requirement in requirements
            ]
            if not requirement_ids or len(requirement_ids) != len(set(requirement_ids)):
                raise GuaranteeValidationError("matrix requirement IDs are missing or duplicate")
            all_requirement_ids.extend(requirement_ids)
            selectors = claim["required_control_selectors"]
            if not isinstance(selectors, list):
                raise GuaranteeValidationError("required_control_selectors must be a list")
            selector_documents: list[str] = []
            for selector in selectors:
                if not isinstance(selector, dict) or set(selector) != {
                    "control_type",
                    "check",
                    "subject_requirement_id",
                }:
                    raise GuaranteeValidationError(
                        "control selector does not match schema"
                    )
                if (
                    not isinstance(selector["control_type"], str)
                    or selector["control_type"] not in CONTROL_TYPES
                ):
                    raise GuaranteeValidationError("selector control_type is invalid")
                if (
                    not isinstance(selector["check"], str)
                    or selector["check"] not in CHECK_NAMES
                ):
                    raise GuaranteeValidationError("selector check is invalid")
                _required_text(
                    selector["subject_requirement_id"],
                    "selector subject_requirement_id",
                )
                if selector.get("subject_requirement_id") not in requirement_ids:
                    raise GuaranteeValidationError(
                        "selector subject requirement does not exist"
                    )
                selector_documents.append(_canonical_json(selector))
            if len(selector_documents) != len(set(selector_documents)):
                raise GuaranteeValidationError("control selectors must be unique")
            if set(claim["required_realization_checks"]) != {
                selector["check"] for selector in selectors
            }:
                raise GuaranteeValidationError(
                    "realization checks do not match control selectors"
                )
        if len(all_requirement_ids) != len(set(all_requirement_ids)):
            raise GuaranteeValidationError("matrix requirement IDs must be globally unique")

    @staticmethod
    def _validate_nonempty_unique_strings(value: object, name: str) -> None:
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or not item.strip() for item in value)
            or len(value) != len(set(value))
        ):
            raise GuaranteeValidationError(
                f"{name} must be a non-empty unique string list"
            )

    @staticmethod
    def _validate_enum_list(
        value: object,
        allowed: set[str],
        name: str,
        *,
        allow_empty: bool = False,
    ) -> None:
        if (
            not isinstance(value, list)
            or (not allow_empty and not value)
            or any(not isinstance(item, str) or item not in allowed for item in value)
            or len(value) != len(set(value))
        ):
            raise GuaranteeValidationError(f"{name} does not match schema")

    def _contains_forbidden(self, value: object, claim: dict) -> bool:
        if not isinstance(value, str):
            return False
        forbidden = set(self.matrix["global_forbidden_wording"])
        forbidden.update(claim["forbidden_wording"])
        return any(phrase in value for phrase in forbidden)

    def _evaluate_claim(
        self,
        task: TaskIdentity,
        claim: dict,
        all_evidence: list[EvidenceRecord],
        all_controls: list[dict],
        evaluated_at: str,
    ) -> dict:
        if task.mode not in claim["applicable_task_modes"]:
            requirement_results = [
                {
                    "requirement_id": requirement["requirement_id"],
                    "subject_ref": f"task:{task.task_id}:mode",
                    "result": "not_applicable",
                    "basis": "inferred",
                    "evidence_refs": [],
                    "inference_from": [f"task:{task.task_id}"],
                    "conflict_refs": [],
                    "exact_scope": task.cwd,
                }
                for requirement in claim["required_evidence"]
            ]
            return self._claim_document(
                claim,
                "not_evaluated",
                requirement_results,
                [],
                task.cwd,
                [],
                evaluated_at,
            )

        requirement_results = [
            self._evaluate_requirement(requirement, claim, task, all_evidence)
            for requirement in claim["required_evidence"]
        ]
        requirement_by_id = {
            result["requirement_id"]: result for result in requirement_results
        }
        evidence_contradicted = any(
            result["result"] == "fail" for result in requirement_results
        )
        evidence_supported = all(
            result["result"] == "pass" for result in requirement_results
        )

        control_state = "supported"
        control_refs: list[str] = []
        control_conflicts: list[str] = []
        for selector in claim["required_control_selectors"]:
            requirement_result = requirement_by_id[selector["subject_requirement_id"]]
            selector_records = [
                record
                for record in all_controls
                if record["control_type"] == selector["control_type"]
                and record["control_id"] == requirement_result["subject_ref"]
                and record["scope"]["boundary"] == requirement_result["exact_scope"]
                and record["checks"][selector["check"]]["exact_scope"]
                == requirement_result["exact_scope"]
            ]
            selector_refs = [record["record_id"] for record in selector_records]
            control_refs.extend(selector_refs)
            if not selector_records:
                if control_state != "contradicted":
                    control_state = "not_evaluated"
                continue
            checks = [record["checks"][selector["check"]] for record in selector_records]
            results = {check["result"] for check in checks}
            observed_fail = any(
                check["result"] == "fail" and check["basis"] == "observed"
                for check in checks
            )
            if observed_fail or {"pass", "fail"}.issubset(results):
                control_state = "contradicted"
                control_conflicts.extend(selector_refs)
            elif not all(
                check["result"] == "pass"
                and check["basis"] in claim["allowed_basis"]
                and self._control_check_material_valid(
                    check,
                    task.task_id,
                    selector["subject_requirement_id"],
                    requirement_result["subject_ref"],
                    requirement_result["exact_scope"],
                )
                for check in checks
            ):
                if control_state != "contradicted":
                    control_state = "not_evaluated"

        if evidence_contradicted or control_state == "contradicted":
            verdict = "contradicted"
        elif evidence_supported and control_state == "supported":
            verdict = "supported"
        else:
            verdict = "not_evaluated"
        conflict_refs = sorted(
            {
                ref
                for result in requirement_results
                for ref in result["conflict_refs"]
            }
            | set(control_conflicts)
        )
        scopes = sorted(
            {
                result["exact_scope"]
                for result in requirement_results
                if result["exact_scope"]
            }
        )
        scope = "; ".join(scopes) if scopes else task.cwd
        return self._claim_document(
            claim,
            verdict,
            requirement_results,
            sorted(set(control_refs)),
            scope,
            conflict_refs,
            evaluated_at,
        )

    def _evaluate_requirement(
        self,
        requirement: dict,
        claim: dict,
        task: TaskIdentity,
        all_evidence: list[EvidenceRecord],
    ) -> dict:
        candidates = [
            record
            for record in all_evidence
            if record.requirement_id == requirement["requirement_id"]
        ]
        if not candidates:
            return {
                "requirement_id": requirement["requirement_id"],
                "subject_ref": f"task:{task.task_id}:unobserved",
                "result": "not_run",
                "basis": "unobserved",
                "evidence_refs": [],
                "inference_from": [],
                "conflict_refs": [],
                "exact_scope": "",
            }

        evidence_refs = sorted(
            record.evidence_id for record in candidates if record.basis == "observed"
        )
        inference_from = sorted(
            {
                ref
                for record in candidates
                if record.basis == "inferred"
                for ref in record.inference_from
            }
        )
        subjects = sorted({record.subject_ref for record in candidates})
        scopes = sorted({record.exact_scope for record in candidates})
        subject_ref = subjects[0] if len(subjects) == 1 else "multiple-subjects"
        exact_scope = scopes[0] if len(scopes) == 1 else "multiple-scopes"
        forbidden_scope = any(
            self._contains_forbidden(record.exact_scope, claim)
            for record in candidates
        )
        if forbidden_scope:
            exact_scope = ""
        record_results = {record.result for record in candidates}
        observed_fail = any(
            record.result == "fail" and record.basis == "observed"
            for record in candidates
        )
        conflict = {"pass", "fail"}.issubset(record_results)
        explicit_conflicts = {
            ref for record in candidates for ref in record.conflict_refs
        }
        if observed_fail or conflict or explicit_conflicts:
            conflict_refs = sorted(
                explicit_conflicts
                | {
                    record.evidence_id
                    for record in candidates
                    if record.result in {"pass", "fail"}
                }
            )
            return {
                "requirement_id": requirement["requirement_id"],
                "subject_ref": subject_ref,
                "result": "fail",
                "basis": "observed" if evidence_refs else "inferred",
                "evidence_refs": evidence_refs,
                "inference_from": inference_from,
                "conflict_refs": conflict_refs,
                "exact_scope": exact_scope,
            }

        complete = (
            all(record.evidence_type == requirement["type"] for record in candidates)
            and len(subjects) == 1
            and len(scopes) == 1
            and all(record.result == "pass" for record in candidates)
            and all(record.basis in claim["allowed_basis"] for record in candidates)
            and not explicit_conflicts
            and not forbidden_scope
            and all(
                all(
                    self._required_evidence_field_material(record, field)
                    for field in requirement["required_fields"]
                )
                for record in candidates
            )
            and all(self._evidence_matches_task(record, task) for record in candidates)
            and all(self._evidence_matches_runtime(record, task) for record in candidates)
            and all(
                self._inference_sources_valid(record, all_evidence, task)
                for record in candidates
            )
            and all(self._evidence_object_valid(record) for record in candidates)
        )
        if complete:
            inferred = any(record.basis == "inferred" for record in candidates)
            return {
                "requirement_id": requirement["requirement_id"],
                "subject_ref": subject_ref,
                "result": "pass",
                "basis": "inferred" if inferred else "observed",
                "evidence_refs": evidence_refs,
                "inference_from": inference_from,
                "conflict_refs": [],
                "exact_scope": exact_scope,
            }
        return {
            "requirement_id": requirement["requirement_id"],
            "subject_ref": subject_ref,
            "result": "unknown",
            "basis": "unobserved",
            "evidence_refs": sorted(record.evidence_id for record in candidates),
            "inference_from": inference_from,
            "conflict_refs": sorted(explicit_conflicts),
            "exact_scope": exact_scope,
        }

    def _evidence_object_valid(self, record: EvidenceRecord) -> bool:
        try:
            self.evidence.read_content(record.evidence_id)
        except (OSError, ValueError):
            return False
        return True

    @staticmethod
    def _evidence_matches_task(record: EvidenceRecord, task: TaskIdentity) -> bool:
        bindings = {
            "target_commit": task.commit,
            "environment": task.environment_ref,
            "environment_ref": task.environment_ref,
            "task_ref": task.task_id,
            "result": record.result,
            "basis": record.basis,
        }
        return all(
            key not in record.fields or record.fields[key] == expected
            for key, expected in bindings.items()
        )

    @staticmethod
    def _required_evidence_field_material(
        record: EvidenceRecord, field: str
    ) -> bool:
        value = record.fields.get(field)
        if record.evidence_type == "event_projection_sequence" and field in {
            "event_head",
            "projected_sequence",
        }:
            return isinstance(value, int) and not isinstance(value, bool) and value >= 0
        return _material(value)

    def _evidence_matches_runtime(
        self, record: EvidenceRecord, task: TaskIdentity
    ) -> bool:
        if record.evidence_type != "event_projection_sequence":
            return True
        try:
            self._validate_timestamp(record.fields.get("checked_at"), "checked_at")
            freshness = self.projections.freshness(task.task_id)
        except (GuaranteeValidationError, OSError, ValueError):
            return False
        return (
            record.subject_ref == f"task:{task.task_id}:projection"
            and record.fields.get("event_head") == freshness.event_head
            and record.fields.get("projected_sequence")
            == freshness.projected_sequence
            and record.fields.get("projection_version") == PROJECTION_VERSION
            and freshness.is_fresh
        )

    def _inference_sources_valid(
        self,
        record: EvidenceRecord,
        all_evidence: list[EvidenceRecord],
        task: TaskIdentity,
    ) -> bool:
        if record.basis != "inferred":
            return True
        sources = {source.evidence_id: source for source in all_evidence}
        for source_id in record.inference_from:
            source = sources.get(source_id)
            if (
                source is None
                or source.evidence_id == record.evidence_id
                or source.task_id != task.task_id
                or source.basis != "observed"
                or source.result != "pass"
                or source.conflict_refs
                or not self._evidence_matches_task(source, task)
                or not self._evidence_object_valid(source)
            ):
                return False
        return True

    def _control_check_material_valid(
        self,
        check: dict,
        task_id: str,
        requirement_id: str,
        subject_ref: str,
        exact_scope: str,
    ) -> bool:
        if check["basis"] == "observed":
            if not check["evidence_refs"] or not check["checked_at"]:
                return False
            try:
                records = [
                    self.evidence.resolve(evidence_id)
                    for evidence_id in check["evidence_refs"]
                ]
                return all(
                    record.task_id == task_id
                    and record.requirement_id == requirement_id
                    and record.subject_ref == subject_ref
                    and record.exact_scope == exact_scope
                    and record.result == check["result"]
                    and record.basis == "observed"
                    and not record.conflict_refs
                    and bool(self.evidence.read_content(record.evidence_id))
                    for record in records
                )
            except (OSError, ValueError):
                return False
        if check["basis"] == "inferred":
            return bool(check["inference_from"] and check["checked_at"])
        return False

    def _claim_document(
        self,
        claim: dict,
        verdict: str,
        requirement_results: list[dict],
        control_refs: list[str],
        scope: str,
        conflict_refs: list[str],
        evaluated_at: str,
    ) -> dict:
        if self._contains_forbidden(scope, claim):
            scope = "scope withheld by wording policy"
        requirement_results = [
            {
                **result,
                "exact_scope": (
                    ""
                    if self._contains_forbidden(result.get("exact_scope"), claim)
                    else result["exact_scope"]
                ),
            }
            for result in requirement_results
        ]
        return {
            "claim_id": claim["claim_id"],
            "verdict": verdict,
            "requirement_results": requirement_results,
            "control_validation_refs": control_refs,
            "scope": scope,
            "conflict_refs": conflict_refs,
            "residual_risks": list(claim["residual_risks"]),
            "permitted_statement": claim["claim"] if verdict == "supported" else None,
            "evaluated_at": evaluated_at,
        }

    def _validate_control_record(self, task: TaskIdentity, record: dict) -> None:
        if not isinstance(record, dict):
            raise GuaranteeValidationError("control record must be an object")
        if set(record) != {
            "schema_version",
            "record_id",
            "control_id",
            "control_type",
            "scope",
            "checks",
        }:
            raise GuaranteeValidationError("control record fields do not match schema")
        if record["schema_version"] != "1.0":
            raise GuaranteeValidationError("control schema version mismatch")
        _required_text(record["record_id"], "record_id")
        _required_text(record["control_id"], "control_id")
        if (
            not isinstance(record["control_type"], str)
            or record["control_type"] not in self.allowed_control_types
        ):
            raise GuaranteeValidationError(
                "control_type is not part of the M0 execution-control schema"
            )
        scope = record["scope"]
        expected_scope = {
            "project_id": task.project_id,
            "worktree_id": task.worktree_id,
            "task_id": task.task_id,
            "environment_ref": task.environment_ref,
        }
        if not isinstance(scope, dict) or set(scope) != set(expected_scope) | {"boundary"}:
            raise GuaranteeValidationError("control scope fields do not match schema")
        if any(scope[key] != value for key, value in expected_scope.items()):
            raise GuaranteeValidationError("control task scope mismatch")
        _required_text(scope["boundary"], "control boundary")
        checks = record["checks"]
        if not isinstance(checks, dict) or set(checks) != CHECK_NAMES:
            raise GuaranteeValidationError("control checks must be independent")
        for check_name, check in checks.items():
            self._validate_control_check(task.task_id, check_name, check)

    def _validate_control_check(
        self, task_id: str, check_name: str, check: dict
    ) -> None:
        required_keys = {
            "result",
            "basis",
            "evidence_refs",
            "inference_from",
            "checked_at",
            "exact_scope",
            "residual_risks",
        }
        if not isinstance(check, dict) or set(check) != required_keys:
            raise GuaranteeValidationError(f"{check_name} check fields do not match schema")
        if (
            not isinstance(check["result"], str)
            or check["result"] not in CONTROL_RESULTS
            or not isinstance(check["basis"], str)
            or check["basis"] not in CONTROL_BASES
        ):
            raise GuaranteeValidationError(f"{check_name} result or basis is invalid")
        for field in ("evidence_refs", "inference_from", "residual_risks"):
            values = check[field]
            if (
                not isinstance(values, list)
                or any(not isinstance(value, str) or not value.strip() for value in values)
                or len(values) != len(set(values))
            ):
                raise GuaranteeValidationError(f"{check_name} {field} must be a unique list")
        if check["result"] == "not_run":
            if (
                check["basis"] != "unobserved"
                or check["evidence_refs"]
                or check["inference_from"]
                or check["checked_at"] is not None
            ):
                raise GuaranteeValidationError(f"{check_name} not_run is not unobserved")
            return
        if check["basis"] == "observed":
            if not check["evidence_refs"] or check["checked_at"] is None:
                raise GuaranteeValidationError(f"{check_name} observed material is missing")
            self._validate_timestamp(check["checked_at"], f"{check_name}.checked_at")
            for evidence_id in check["evidence_refs"]:
                try:
                    evidence = self.evidence.resolve(evidence_id)
                except ValueError as error:
                    raise GuaranteeValidationError(
                        f"{check_name} evidence ref is unresolved: {evidence_id}"
                    ) from error
                if evidence.task_id != task_id:
                    raise GuaranteeValidationError(
                        f"{check_name} evidence ref belongs to another task"
                    )
                try:
                    self.evidence.read_content(evidence_id)
                except (OSError, ValueError) as error:
                    raise GuaranteeValidationError(
                        f"{check_name} evidence ref failed integrity validation"
                    ) from error
        elif check["basis"] == "inferred":
            if not check["inference_from"] or check["checked_at"] is None:
                raise GuaranteeValidationError(f"{check_name} inference material is missing")
            self._validate_timestamp(check["checked_at"], f"{check_name}.checked_at")
        else:
            raise GuaranteeValidationError(
                f"{check_name} unobserved basis requires not_run"
            )
        if check["result"] in {"pass", "fail"}:
            _required_text(check["exact_scope"], f"{check_name}.exact_scope")

    def _list_control_validations(self, task_id: str) -> list[dict]:
        task = self.identities.get_task(task_id)
        rows = self.catalog.connection.execute(
            """
            SELECT record_id, task_id, record_json, fingerprint
            FROM control_validations
            WHERE task_id=? ORDER BY record_id
            """,
            (task_id,),
        ).fetchall()
        records: list[dict] = []
        for row in rows:
            document = row["record_json"]
            expected_fingerprint = hashlib.sha256(
                document.encode("utf-8")
            ).hexdigest()
            if row["fingerprint"] != expected_fingerprint:
                raise GuaranteeValidationError(
                    "authoritative control validation integrity failure"
                )
            try:
                record = json.loads(document)
            except json.JSONDecodeError as error:
                raise GuaranteeValidationError(
                    "authoritative control validation is not valid JSON"
                ) from error
            if row["task_id"] != task_id or record.get("record_id") != row["record_id"]:
                raise GuaranteeValidationError(
                    "authoritative control validation scope mismatch"
                )
            self._validate_control_record(task, record)
            records.append(record)
        return records

    @staticmethod
    def _task_document(task: TaskIdentity) -> dict:
        return {
            "project_id": task.project_id,
            "worktree_id": task.worktree_id,
            "task_id": task.task_id,
            "mode": task.mode,
            "target_commit": task.commit,
            "environment_ref": task.environment_ref,
        }

    @staticmethod
    def _validate_timestamp(value: object, name: str) -> None:
        _required_text(value, name)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as error:
            raise GuaranteeValidationError(f"{name} is not ISO-8601") from error
        if parsed.tzinfo is None:
            raise GuaranteeValidationError(f"{name} must include a timezone")

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .assurance import fingerprint
from .dashboard_sources import (
    EvidenceView,
    SourceClosure,
    resolve_evidence,
    validate_m3_source,
    validate_m4_source,
)
from .evidence import EvidenceRecord, EvidenceStore
from .events import EventLog, EventRecord
from .guarantees import GuaranteeEvaluator
from .identity import TaskIdentity
from .projections import Freshness, ProjectionStatus


_VISIBLE_RESULTS = {
    "pass": "passed",
    "fail": "failed",
    "not_run": "not_run",
    "missing": "unknown",
    "inconclusive": "inconclusive",
}
_TASK_FIELDS = ("project_id", "worktree_id", "task_id", "environment_ref", "mode")
_CONTROL_NAMES = ("config", "agents", "rules", "hooks", "sandbox", "approval")
_STAGES = ("configured", "loaded", "enforced")
_MATRIX_PATH = Path(__file__).resolve().parents[2] / "docs/product/guarantee-matrix.v1.json"
_BASELINE_FIELDS = {
    "baseline_version",
    "baseline_id",
    "version",
    "predecessor_ref",
    "project_id",
    "worktree_id",
    "environment_ref",
    "profile_ref",
    "interview_ref",
    "source_fingerprints",
    "sources",
    "commands",
    "sensitive_paths",
    "external_services",
    "hwpx_tool_contract",
    "unobserved",
    "event_refs",
    "evidence_refs",
    "fingerprint",
}
_CONTEXT_STATUS_FIELDS = {
    "report_version",
    "matrix_version",
    "manifest_ref",
    "active_context",
    "active_controls",
    "excluded_context",
    "applicability_results",
    "lint_findings",
    "claim_results",
}
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONTEXT_DECISIONS = {
    "maintain",
    "add_for_task",
    "exclude_for_task",
    "replace_with_specific",
    "forbidden",
    "unobserved",
}


@dataclass(frozen=True)
class TaskReviewView:
    task: dict
    summary: dict
    freshness: dict
    completeness: dict
    diagram: dict
    relations: tuple[dict, ...]
    verification: tuple[dict, ...]
    guarantees: tuple[dict, ...]
    harness: dict
    assurance: dict
    decision: dict
    history: tuple[dict, ...]
    evidence: tuple[EvidenceView, ...]
    assembled_at: str


def _iso_time(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("assembled_at must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("assembled_at must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise ValueError("assembled_at must include a timezone")
    return parsed.isoformat()


def _unavailable(source: str) -> SourceClosure:
    return SourceClosure(
        source=source,
        scope="project" if source == "m3" else "task",
        status="unavailable",
        task_applicable=False,
        observed_at=None,
        fingerprint=None,
        reasons=(f"{source} source unavailable",),
    )


def _task_identity(task: TaskIdentity) -> dict:
    return {
        "project_id": task.project_id,
        "worktree_id": task.worktree_id,
        "task_id": task.task_id,
        "mode": task.mode,
        "commit": task.commit,
        "branch": task.branch,
        "environment_ref": task.environment_ref,
        "created_at": task.created_at,
    }


def _task_matches(task: TaskIdentity, value: object) -> bool:
    if not isinstance(value, dict):
        return False
    expected = _task_identity(task)
    return all(value.get(field) == expected[field] for field in _TASK_FIELDS)


def _contract_source(
    task: TaskIdentity,
    contract: dict | None,
    assurance_packet: dict | None = None,
    m4: SourceClosure | None = None,
) -> dict:
    if not isinstance(contract, dict):
        return {"status": "unavailable"}
    task_value = contract.get("task")
    if not _task_matches(task, task_value):
        return {"status": "mismatch"}
    contract_id = contract.get("contract_id")
    source_fingerprint = contract.get("source_contract_fingerprint", contract.get("fingerprint"))
    if not isinstance(contract_id, str) or not isinstance(source_fingerprint, str):
        return {"status": "invalid"}
    actual_fingerprint = contract.get("fingerprint")
    try:
        expected_fingerprint = fingerprint(
            {key: value for key, value in contract.items() if key != "fingerprint"}
        )
    except (TypeError, ValueError):
        return {"status": "invalid"}
    if actual_fingerprint != expected_fingerprint:
        return {"status": "invalid"}
    if (
        m4 is not None
        and m4.status == "closed"
        and isinstance(assurance_packet, dict)
        and source_fingerprint != assurance_packet.get("contract_fingerprint")
    ):
        return {"status": "mismatch"}
    return {
        "status": "closed",
        "contract_id": contract_id,
        "fingerprint": source_fingerprint,
        "goal": task_value.get("goal") if isinstance(task_value.get("goal"), str) else None,
    }


def _source_backed_summary(
    task: TaskIdentity,
    execution_contract: dict | None,
    assurance_packet: dict | None,
    m3: SourceClosure,
    m4: SourceClosure,
) -> dict:
    contract = _contract_source(task, execution_contract, assurance_packet, m4)
    goal = contract.get("goal") if contract.get("status") == "closed" else None
    changed_paths: tuple[str, ...] = ()
    declared_relations: tuple[str, ...] = ()
    gate = "not_evaluated"
    if m4.status == "closed" and isinstance(assurance_packet, dict):
        changed_paths = tuple(
            item["path"]
            for item in assurance_packet["impact"]["changed_paths"]
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        )
        declared_relations = tuple(
            item["relation_id"]
            for item in assurance_packet["impact"]["relations"]
            if isinstance(item, dict) and isinstance(item.get("relation_id"), str)
        )
        gate = assurance_packet["gate"]["decision"]
    warnings = []
    if contract["status"] != "closed":
        warnings.append("Task Contract is unavailable or does not close to this Task")
    if not m3.task_applicable:
        warnings.append("M3 runtime provenance is not current-Task control evidence")
    if not m4.task_applicable:
        warnings.append("M4 Assurance is unavailable or does not close to this Task")
    return {
        "disclosure_order": ("summary", "trace", "evidence", "decision"),
        "goal": goal,
        "change_statement": (
            goal if goal is not None else "feature summary has no closed source"
        ),
        "changed_paths": changed_paths,
        "declared_relations": declared_relations,
        "gate": gate,
        "warnings": tuple(warnings),
        "contract": contract,
    }


def _freshness_view(task: TaskIdentity, projection: ProjectionStatus, freshness: Freshness) -> dict:
    if projection.task_id != task.task_id or freshness.task_id != task.task_id:
        raise ValueError("Projection freshness Task binding mismatch")
    if projection.state == "failed" or freshness.projection_state == "failed":
        state = "failed"
    elif (
        projection.state == "ready"
        and freshness.projection_state == "ready"
        and freshness.is_fresh
        and freshness.event_head == freshness.projected_sequence
        and projection.projected_sequence == freshness.projected_sequence
    ):
        state = "fresh"
    else:
        state = "stale"
    return {
        "state": state,
        "event_head": freshness.event_head,
        "projected_sequence": freshness.projected_sequence,
        "lag": max(0, freshness.event_head - freshness.projected_sequence),
        "projection_state": freshness.projection_state,
        "last_error": freshness.last_error or projection.last_error,
        "projection_updated_at": projection.updated_at,
    }


def _matching_guarantee(
    task: TaskIdentity,
    report: dict | None,
    evidence_store: EvidenceStore,
) -> bool:
    if not isinstance(report, dict):
        return False
    try:
        evaluator = GuaranteeEvaluator(evidence_store.catalog, evidence_store, _MATRIX_PATH)
        evaluator.validate_report(report)
    except (OSError, ValueError):
        return False
    identity = report.get("task")
    claims = report.get("claim_results")
    return bool(
        _task_matches(task, identity)
        and isinstance(identity, dict)
        and identity.get("target_commit") == task.commit
        and isinstance(claims, list)
        and claims
    )


def _material(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def _namespaced(value: object, namespace: str) -> bool:
    return isinstance(value, str) and (
        value == namespace or value.startswith(namespace + ":")
    )


def _direct_evidence(
    store: EvidenceStore,
    records: list[EvidenceRecord],
    task: TaskIdentity,
) -> EvidenceRecord | None:
    required_fields = (
        "input",
        "expected",
        "actual",
        "environment",
    )
    candidates = [
        record
        for record in records
        if record.task_id == task.task_id
        and record.requirement_id == "M5-06"
        and record.evidence_type == "direct_feature_probe"
        and record.basis == "observed"
        and record.result in {"pass", "fail", "inconclusive"}
        and _namespaced(record.subject_ref, "subject:hwpx")
        and (
            record.fields.get("adapter") == "hwpx"
            or _namespaced(record.fields.get("adapter_ref"), "adapter:hwpx")
        )
        and all(_material(record.fields.get(field)) for field in required_fields)
        and record.fields.get("environment") == task.environment_ref
        and record.fields.get("task_ref", task.task_id) == task.task_id
        and record.fields.get("target_commit", task.commit) == task.commit
        and (
            _material(record.fields.get("generated_output"))
            or _material(record.fields.get("generated_files"))
            or _material(record.fields.get("tool_error"))
        )
        and isinstance(record.fields.get("human_observation"), str)
        and bool(record.fields["human_observation"].strip())
    ]
    for record in reversed(candidates):
        try:
            resolve_evidence(
                store,
                task_id=task.task_id,
                evidence_id=record.evidence_id,
                assurance_packet=None,
            )
        except (OSError, ValueError):
            continue
        return record
    return None


def _completeness(
    task: TaskIdentity,
    m3: SourceClosure,
    m4: SourceClosure,
    m2: dict[str, str],
    execution_contract: dict | None,
    assurance_packet: dict | None,
    guarantee_matches: bool,
    direct: EvidenceRecord | None,
) -> dict:
    missing = []
    if m2["project_baseline"] != "closed":
        missing.append("project_baseline")
    if m2["context_status"] != "closed":
        missing.append("context_status")
    if _contract_source(task, execution_contract, assurance_packet, m4).get("status") != "closed":
        missing.append("execution_contract")
    if not m3.task_applicable:
        missing.append("m3_task_control")
    if not m4.task_applicable:
        missing.append("m4_assurance")
    if not guarantee_matches:
        missing.append("task_guarantee_report")
    if direct is None:
        missing.append("human_feature_observation")
    return {
        "state": "complete" if not missing else "unobserved",
        "missing": tuple(missing),
        "source_status": {"m3": m3.status, "m4": m4.status},
    }


def _m2_references_close(
    value: object, *, store: EvidenceStore, task: TaskIdentity,
    event_ids: set[str], manifest_ref: str | None, source_refs: frozenset[str] = frozenset(),
) -> bool:
    if isinstance(value, list):
        return all(_m2_references_close(
            item, store=store, task=task, event_ids=event_ids,
            manifest_ref=manifest_ref, source_refs=source_refs,
        ) for item in value)
    if not isinstance(value, dict):
        return True
    local_sources = frozenset(value.get("source_refs", []))
    local_sources |= frozenset(value[key] for key in ("source_ref", "source_id") if key in value)
    scoped_sources = local_sources or source_refs
    if not set(value.get("event_refs", [])) <= event_ids:
        return False
    for reference in value.get("evidence_refs", []) + value.get("conflict_refs", []):
        resolve_evidence(store, task_id=task.task_id, evidence_id=reference, assurance_packet=None)
        record = store.resolve(reference)
        if (
            record.fields.get("environment", task.environment_ref) != task.environment_ref
            or record.fields.get("target_commit", task.commit) != task.commit
            or record.fields.get("task_ref", task.task_id) != task.task_id
        ):
            return False
        if manifest_ref is not None and (
            record.fields.get("manifest_ref") != manifest_ref
            or record.fields.get("task_ref") != task.task_id
        ):
            return False
        if scoped_sources:
            declared = record.fields.get("source_refs", [])
            if not isinstance(declared, list) or not all(isinstance(ref, str) for ref in declared):
                return False
            record_sources = set(declared)
            if "source_ref" in record.fields:
                if not isinstance(record.fields["source_ref"], str):
                    return False
                record_sources.add(record.fields["source_ref"])
            if not scoped_sources <= record_sources:
                return False
    return all(_m2_references_close(
        item, store=store, task=task, event_ids=event_ids,
        manifest_ref=manifest_ref, source_refs=scoped_sources,
    ) for item in value.values() if isinstance(item, (dict, list)))


def _m2_source(
    *, task: TaskIdentity, artifact: dict | None, kind: str,
    store: EvidenceStore, records: list[EvidenceRecord], events: list[EventRecord],
    execution_contract: dict | None, assurance_packet: dict | None, m4: SourceClosure,
) -> str:
    if artifact is None:
        return "unavailable"
    baseline = kind == "project_baseline"
    if not (_valid_baseline(task, artifact) if baseline else _valid_context_status(artifact)):
        return "invalid"
    if baseline and (
        _contract_source(task, execution_contract, assurance_packet, m4).get("status") != "closed"
        or execution_contract.get("baseline_ref") != artifact["baseline_id"]
        or execution_contract.get("baseline_fingerprint") != artifact["fingerprint"]
    ):
        return "unobserved"
    artifact_ref = artifact["baseline_id" if baseline else "manifest_ref"]
    artifact_fingerprint = fingerprint(artifact)
    candidates = [record for record in records if (
        record.task_id == task.task_id
        and record.evidence_type == "active_configuration"
        and record.requirement_id == "M5-05"
        and record.collection_method == "m2-validated-artifact"
        and record.result == "pass" and record.basis == "observed"
        and record.subject_ref == artifact_ref
        and record.fields.get("artifact_kind") == kind
        and record.fields.get("artifact_ref") == artifact_ref
        and record.fields.get("artifact_fingerprint") == artifact_fingerprint
        and record.fields.get("environment") == task.environment_ref
        and record.fields.get("target_commit") == task.commit
        and "sha256:" + record.content_hash == artifact_fingerprint
    )]
    for record in candidates:
        try:
            resolve_evidence(store, task_id=task.task_id, evidence_id=record.evidence_id, assurance_packet=None)
            if _m2_references_close(
                artifact, store=store, task=task,
                event_ids={event.event_id for event in events if event.task_id == task.task_id},
                manifest_ref=None if baseline else artifact_ref,
            ):
                return "closed"
        except (OSError, ValueError):
            continue
    return "unobserved"


def _valid_baseline(task: TaskIdentity, baseline: dict | None) -> bool:
    if not isinstance(baseline, dict) or set(baseline) != _BASELINE_FIELDS:
        return False
    try:
        expected = fingerprint(
            {key: value for key, value in baseline.items() if key != "fingerprint"}
        )
    except (TypeError, ValueError):
        return False
    return bool(
        baseline.get("baseline_version") == "1.0"
        and isinstance(baseline.get("version"), int)
        and not isinstance(baseline.get("version"), bool)
        and baseline["version"] >= 1
        and baseline.get("fingerprint") == expected
        and baseline.get("project_id") == task.project_id
        and baseline.get("worktree_id") == task.worktree_id
        and baseline.get("environment_ref") == task.environment_ref
        and all(
            isinstance(baseline.get(field), str) and bool(baseline[field])
            for field in ("baseline_id", "project_id", "worktree_id", "environment_ref")
        )
        and all(
            isinstance(baseline.get(field), str) and _HASH.fullmatch(baseline[field])
            for field in ("profile_ref", "interview_ref", "fingerprint")
        )
        and (
            baseline["predecessor_ref"] is None
            if baseline["version"] == 1
            else isinstance(baseline["predecessor_ref"], str)
            and bool(baseline["predecessor_ref"])
        )
        and all(
            isinstance(baseline.get(field), list)
            for field in (
                "sources",
                "commands",
                "sensitive_paths",
                "external_services",
                "unobserved",
                "event_refs",
                "evidence_refs",
            )
        )
        and isinstance(baseline.get("source_fingerprints"), dict)
        and all(
            isinstance(key, str)
            and bool(key)
            and isinstance(value, str)
            and _HASH.fullmatch(value)
            for key, value in baseline["source_fingerprints"].items()
        )
        and _valid_sources(baseline["sources"], baseline["source_fingerprints"])
        and all(_valid_command(item) for item in baseline["commands"])
        and all(_valid_sensitive_path(item) for item in baseline["sensitive_paths"])
        and all(_valid_service(item) for item in baseline["external_services"])
        and _valid_hwpx_contract(baseline.get("hwpx_tool_contract"))
        and all(_valid_unobserved(item) for item in baseline["unobserved"])
        and _valid_refs(baseline["event_refs"])
        and _valid_refs(baseline["evidence_refs"])
    )


def _exact_object(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _valid_refs(value: object, *, required: bool = False) -> bool:
    return bool(
        isinstance(value, list)
        and (not required or value)
        and all(_text(item) for item in value)
        and len(value) == len(set(value))
    )


def _unique_objects(values: list[object]) -> bool:
    try:
        return len(values) == len({fingerprint(item) for item in values})
    except (TypeError, ValueError):
        return False


def _valid_check(value: object) -> bool:
    if not _exact_object(value, {"result", "basis", "evidence_refs"}):
        return False
    refs = value["evidence_refs"]
    return bool(
        _valid_refs(refs)
        and (
            value["result"] == "pass"
            and value["basis"] == "observed"
            and refs
            or value["result"] == "not_run"
            and value["basis"] == "unobserved"
            and not refs
        )
    )


def _valid_source(value: object) -> bool:
    if not _exact_object(
        value,
        {"source_id", "source_type", "path", "content_hash", "scope", "freshness", "realization"},
    ):
        return False
    freshness = value["freshness"]
    realization = value["realization"]
    return bool(
        all(_text(value[field]) for field in ("source_id", "path", "scope"))
        and value["source_type"]
        in {
            "agents_instruction",
            "project_contract",
            "project_manifest",
            "codex_config",
            "rule",
            "hook",
            "hwpx_tool_contract",
            "external_service_declaration",
        }
        and isinstance(value["content_hash"], str)
        and _HASH.fullmatch(value["content_hash"])
        and _exact_object(freshness, {"status", "basis", "checked_at"})
        and freshness["status"] == "current"
        and freshness["basis"] == "observed"
        and _text(freshness["checked_at"])
        and _exact_object(realization, set(_STAGES))
        and all(_valid_check(realization[stage]) for stage in _STAGES)
    )


def _valid_sources(values: list[object], source_fingerprints: dict) -> bool:
    return bool(
        _unique_objects(values)
        and all(_valid_source(item) for item in values)
        and source_fingerprints
        == {item["source_id"]: item["content_hash"] for item in values}
    )


def _valid_command(value: object) -> bool:
    return bool(
        _exact_object(value, {"kind", "command", "source_ref"})
        and all(_text(value[field]) for field in ("kind", "command", "source_ref"))
    )


def _valid_sensitive_path(value: object) -> bool:
    return bool(
        _exact_object(value, {"path", "basis", "value_exposed"})
        and _text(value["path"])
        and value["basis"] == "observed"
        and value["value_exposed"] is False
    )


def _valid_service(value: object) -> bool:
    return bool(
        _exact_object(value, {"name", "purpose", "endpoint_host"})
        and all(isinstance(value[field], str) for field in ("name", "purpose", "endpoint_host"))
    )


def _valid_hwpx_contract(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("basis") == "unobserved":
        return bool(
            _exact_object(value, {"basis", "tools", "reason"})
            and value["tools"] == []
            and _text(value["reason"])
        )
    return bool(
        value.get("basis") == "observed"
        and _exact_object(value, {"basis", "tools", "source_ref"})
        and isinstance(value["tools"], list)
        and _unique_objects(value["tools"])
        and all(
            _exact_object(tool, {"name", "input", "output"})
            and all(isinstance(tool[field], str) for field in ("name", "input", "output"))
            for tool in value["tools"]
        )
        and isinstance(value["source_ref"], str)
    )


def _valid_unobserved(value: object) -> bool:
    return bool(
        _exact_object(value, {"path", "basis", "reason"})
        and isinstance(value["path"], str)
        and value["basis"] == "unobserved"
        and isinstance(value["reason"], str)
    )


def _valid_context_status(status: dict | None) -> bool:
    if not _exact_object(status, _CONTEXT_STATUS_FIELDS):
        return False
    if not (
        status["report_version"] == "1.0"
        and status["matrix_version"] == "1.5-proposed-1"
        and _text(status["manifest_ref"])
    ):
        return False
    source_fields = {"source_ref", "evidence_refs"}
    excluded_fields = {"source_ref", "reason", "evidence_refs"}
    applicability_fields = {"source_ref", "decision", "evidence_refs"}
    lint_fields = {
        "finding_id", "rule_id", "source_refs", "locations", "impact", "suggestion", "evidence_refs"
    }
    claim_fields = {
        "claim_id", "category", "verdict", "evidence_refs", "conflict_refs",
        "residual_risks", "permitted_statement",
    }
    active = status["active_context"] + status["active_controls"]
    claims = status["claim_results"]
    return bool(
        all(
            isinstance(status[field], list) and _unique_objects(status[field])
            for field in (
                "active_context", "active_controls", "excluded_context",
                "applicability_results", "lint_findings", "claim_results",
            )
        )
        and all(
            _exact_object(item, source_fields)
            and _text(item["source_ref"])
            and _valid_refs(item["evidence_refs"], required=True)
            for item in active
        )
        and all(
            _exact_object(item, excluded_fields)
            and _text(item["source_ref"])
            and _text(item["reason"])
            and _valid_refs(item["evidence_refs"])
            for item in status["excluded_context"]
        )
        and all(
            _exact_object(item, applicability_fields)
            and _text(item["source_ref"])
            and item["decision"] in _CONTEXT_DECISIONS
            and _valid_refs(item["evidence_refs"])
            for item in status["applicability_results"]
        )
        and all(
            _exact_object(item, lint_fields)
            and all(_text(item[field]) for field in ("finding_id", "rule_id", "impact", "suggestion"))
            and all(_valid_refs(item[field]) for field in ("source_refs", "locations", "evidence_refs"))
            for item in status["lint_findings"]
        )
        and len(claims) == 6
        and len({item.get("claim_id") for item in claims if isinstance(item, dict)}) == 6
        and all(_valid_context_claim(item, claim_fields) for item in claims)
    )


def _valid_context_claim(value: object, fields: set[str]) -> bool:
    if not _exact_object(value, fields):
        return False
    verdict = value["verdict"]
    return bool(
        isinstance(value["claim_id"], str)
        and re.fullmatch(r"CGM-[0-9]{3}", value["claim_id"])
        and _text(value["category"])
        and verdict in {"supported", "contradicted", "not_evaluated"}
        and _valid_refs(value["evidence_refs"])
        and _valid_refs(value["conflict_refs"])
        and _valid_refs(value["residual_risks"], required=True)
        and (
            verdict == "supported"
            and bool(value["evidence_refs"])
            and not value["conflict_refs"]
            and _text(value["permitted_statement"])
            or verdict in {"contradicted", "not_evaluated"}
            and value["permitted_statement"] is None
        )
    )


def _bounded_diagram(
    task: TaskIdentity,
    baseline: dict | None,
    execution_contract: dict | None,
    assurance_packet: dict | None,
    m4: SourceClosure,
    baseline_closed: bool,
) -> dict:
    if m4.status != "closed" or not isinstance(assurance_packet, dict):
        return {"state": "unobserved", "kind": None, "nodes": (), "edges": ()}
    relations = assurance_packet["impact"].get("relations", [])
    contract = _contract_source(task, execution_contract, assurance_packet, m4)
    draft = execution_contract.get("assurance_draft") if isinstance(execution_contract, dict) else None
    hypotheses = draft.get("impact_hypotheses") if isinstance(draft, dict) else None
    declared_relation_refs = {
        reference
        for hypothesis in hypotheses or []
        if isinstance(hypothesis, dict)
        for reference in hypothesis.get("relation_refs", [])
        if isinstance(reference, str)
    }
    relation_ids = {
        relation.get("relation_id")
        for relation in relations
        if isinstance(relation, dict)
    }
    sources_close = bool(
        contract.get("status") == "closed"
        and baseline_closed
        and execution_contract.get("baseline_ref") == baseline.get("baseline_id")
        and execution_contract.get("baseline_fingerprint") == baseline.get("fingerprint")
        and isinstance(hypotheses, list)
        and hypotheses
        and relation_ids <= declared_relation_refs
    )
    if not relations or not sources_close:
        return {"state": "unobserved", "kind": None, "nodes": (), "edges": ()}
    node_map: dict[str, dict] = {}
    edges = []
    for relation in relations:
        relation_id = relation["relation_id"]
        target = relation["target_ref"]
        node_map.setdefault(
            target,
            {"node_id": target, "kind": "declared_target", "source_ref": relation_id},
        )
        for path in relation.get("changed_paths", []):
            path_ref = f"changed:{path}"
            node_map.setdefault(
                path_ref,
                {"node_id": path_ref, "kind": "changed_path", "source_ref": relation_id},
            )
            edges.append(
                {
                    "from": path_ref,
                    "to": target,
                    "relation_type": relation["relation_type"],
                    "source_ref": relation_id,
                    "evidence_refs": tuple(relation.get("evidence_refs", [])),
                }
            )
    return {
        "state": "observed",
        "kind": "dependency_impact",
        "nodes": tuple(node_map[key] for key in sorted(node_map)),
        "edges": tuple(sorted(edges, key=lambda item: (item["from"], item["to"], item["source_ref"]))),
    }


def _relations(assurance_packet: dict | None, m4: SourceClosure) -> tuple[dict, ...]:
    if m4.status != "closed" or not isinstance(assurance_packet, dict):
        return ()
    draft = assurance_packet["contract_snapshot"]["assurance_draft"]
    hard_criteria = {
        item["criterion_id"]
        for item in draft["criteria"]
        if item["block_level"] == "hard"
    }
    hard_tests = {
        test_id
        for mapping in draft["mappings"]
        if mapping["criterion_id"] in hard_criteria
        for test_id in mapping["test_ids"]
    }
    gate = assurance_packet["gate"]["decision"]
    rows = []
    for relation in assurance_packet["impact"].get("relations", []):
        if relation["relation_type"] == "test" and (
            relation["target_ref"] in hard_tests or gate == "hard_block"
        ):
            priority = "required"
        elif gate == "soft_block":
            priority = "recommended"
        else:
            priority = "reference"
        rows.append(
            {
                "relation_id": relation["relation_id"],
                "relation_type": relation["relation_type"],
                "target_ref": relation["target_ref"],
                "changed_paths": tuple(relation.get("changed_paths", [])),
                "basis": relation["basis"],
                "evidence_refs": tuple(relation.get("evidence_refs", [])),
                "priority": priority,
            }
        )
    for item in assurance_packet["impact"].get("unobserved", []):
        area = item.get("area") if isinstance(item, dict) else None
        reason = item.get("reason") if isinstance(item, dict) else None
        if not isinstance(area, str) or not area or not isinstance(reason, str) or not reason:
            continue
        changed_paths = (area.removeprefix("changed_path:"),) if area.startswith("changed_path:") else ()
        rows.append(
            {
                "relation_id": "unobserved:" + fingerprint({"area": area, "reason": reason})[7:23],
                "relation_type": "unobserved",
                "target_ref": area,
                "changed_paths": changed_paths,
                "basis": "unobserved",
                "evidence_refs": (),
                "priority": "recommended",
                "reason": reason,
            }
        )
    priority_order = {"required": 0, "recommended": 1, "reference": 2}
    return tuple(
        sorted(rows, key=lambda item: (priority_order[item["priority"]], item["relation_id"]))
    )


def _visible_result(value: object) -> str:
    return _VISIBLE_RESULTS.get(value, "unknown")


def _verification(
    assurance_packet: dict | None,
    m4: SourceClosure,
    direct: EvidenceRecord | None,
) -> tuple[dict, ...]:
    rows = []
    if m4.status == "closed" and isinstance(assurance_packet, dict):
        for receipt in assurance_packet["after"].get("receipts", []):
            rows.append(
                {
                    "kind": "test",
                    "test_id": receipt["test_id"],
                    "subject_ref": receipt["subject_ref"],
                    "result": _visible_result(receipt["result"]),
                    "source_result": receipt["result"],
                    "basis": receipt["basis"],
                    "evidence_refs": tuple(receipt.get("evidence_refs", [])),
                }
            )
        for gap in assurance_packet["gaps"].get("gaps", []):
            rows.append(
                {
                    "kind": "gap",
                    "gap_id": gap["gap_id"],
                    "criterion_id": gap["criterion_id"],
                    "result": (
                        "no_adequate_test"
                        if gap["kind"] == "no_adequate_test"
                        else "unknown"
                    ),
                    "source_result": gap["kind"],
                    "basis": "observed",
                    "evidence_refs": (),
                }
            )
    rows.append(
        {
            "kind": "direct_feature_validation",
            "subject_ref": direct.subject_ref if direct is not None else "subject:direct-feature",
            "result": _visible_result(direct.result) if direct is not None else "unknown",
            "source_result": direct.result if direct is not None else "not_run",
            "basis": direct.basis if direct is not None else "unobserved",
            "evidence_refs": (direct.evidence_id,) if direct is not None else (),
        }
    )
    return tuple(rows)


def _guarantees(
    report: dict | None, guarantee_matches: bool
) -> tuple[dict, ...]:
    if not guarantee_matches:
        claim_ids = []
        if isinstance(report, dict) and isinstance(report.get("claim_results"), list):
            claim_ids = [
                claim.get("claim_id")
                for claim in report["claim_results"]
                if isinstance(claim, dict)
                and isinstance(claim.get("claim_id"), str)
                and claim["claim_id"]
            ]
        if not claim_ids:
            claim_ids = ["task_guarantees"]
        return tuple(
            {
                "claim_id": claim_id,
                "status": "not_evaluated",
                "verdict": None,
                "basis": "unobserved",
                "evidence_refs": (),
            }
            for claim_id in dict.fromkeys(claim_ids)
        )
    rows = []
    for result in report["claim_results"]:
        requirement_refs = tuple(
            evidence_id
            for requirement in result.get("requirement_results", [])
            if isinstance(requirement, dict)
            for evidence_id in requirement.get("evidence_ids", [])
            if isinstance(evidence_id, str)
        )
        rows.append(
            {
                "claim_id": result.get("claim_id"),
                "status": result.get("verdict", "not_evaluated"),
                "verdict": result.get("verdict"),
                "basis": (
                    "observed"
                    if result.get("verdict") in {"supported", "contradicted"}
                    else "unobserved"
                ),
                "permitted_statement": result.get("permitted_statement"),
                "evidence_refs": requirement_refs,
                "residual_risks": tuple(result.get("residual_risks", [])),
            }
        )
    return tuple(rows)


def _unobserved_controls(reason: str) -> dict:
    return {
        control: {
            stage: {
                "result": "not_run",
                "basis": "unobserved",
                "evidence_refs": (),
                "reason": reason,
            }
            for stage in _STAGES
        }
        for control in _CONTROL_NAMES
    }


def _artifact_ref(value: dict | None, id_field: str, *, closure: str) -> dict:
    if closure != "closed":
        return {"status": closure}
    return {
        "status": "observed",
        id_field: value.get(id_field),
        "fingerprint": value.get("fingerprint"),
    }


def _harness(
    task: TaskIdentity,
    baseline: dict | None,
    context_status: dict | None,
    m3_packet: dict | None,
    m3: SourceClosure,
    m2: dict[str, str],
) -> dict:
    project_controls = None
    imported_controls = None
    if m3.status in {"closed", "mismatch"} and isinstance(m3_packet, dict):
        project_controls = copy.deepcopy(m3_packet["managed"]["controls"])
        imported_controls = copy.deepcopy(m3_packet["imported"]["controls"])
    task_controls = (
        copy.deepcopy(project_controls)
        if m3.task_applicable and project_controls is not None
        else _unobserved_controls("M3 task_ref does not close to this Task")
    )
    return {
        "baseline": _artifact_ref(
            baseline, "baseline_id", closure=m2["project_baseline"]
        ),
        "context_status": _artifact_ref(
            context_status,
            "manifest_ref",
            closure=m2["context_status"],
        ),
        "source": {
            "scope": m3.scope,
            "status": m3.status,
            "task_applicable": m3.task_applicable,
            "observed_at": m3.observed_at,
            "fingerprint": m3.fingerprint,
            "reasons": m3.reasons,
        },
        "project_controls": project_controls,
        "controls": task_controls,
        "imported_controls": imported_controls,
    }


def _assurance(assurance_packet: dict | None, m4: SourceClosure) -> dict:
    source = {
        "scope": m4.scope,
        "status": m4.status,
        "task_applicable": m4.task_applicable,
        "observed_at": m4.observed_at,
        "fingerprint": m4.fingerprint,
        "reasons": m4.reasons,
    }
    if m4.status != "closed" or not isinstance(assurance_packet, dict):
        return {"source": source, "gate": {"decision": "not_evaluated", "basis": "unobserved"}}
    gate = assurance_packet["gate"]
    return {
        "source": source,
        "packet_id": assurance_packet["packet_id"],
        "contract_fingerprint": assurance_packet["contract_fingerprint"],
        "gate": {
            "decision": gate["decision"],
            "basis": gate["basis"],
            "fingerprint": gate["fingerprint"],
            "hard_reasons": tuple(gate.get("hard_reasons", [])),
            "soft_reasons": tuple(gate.get("soft_reasons", [])),
            "evidence_refs": tuple(gate.get("evidence_refs", [])),
        },
    }


def _decision(
    projection: ProjectionStatus,
    freshness_view: dict,
    assurance_packet: dict | None,
    m4: SourceClosure,
) -> dict:
    gate = (
        assurance_packet["gate"]["decision"]
        if m4.status == "closed" and isinstance(assurance_packet, dict)
        else "not_evaluated"
    )
    allowed = ["revise", "reject", "additional_validation"]
    if gate != "hard_block":
        allowed.insert(0, "accept")
    if gate == "soft_block":
        allowed.append("risk_acceptance")
    references = (
        projection.projection.get("assurance", {}).get("references", [])
        if isinstance(projection.projection, dict)
        and isinstance(projection.projection.get("assurance", {}), dict)
        else []
    )
    latest = references[-1] if isinstance(references, list) and references else None
    packet_closed_in_projection = (
        isinstance(latest, dict)
        and isinstance(assurance_packet, dict)
        and latest.get("packet_fingerprint") == assurance_packet.get("fingerprint")
        and latest.get("gate_fingerprint") == assurance_packet.get("gate", {}).get("fingerprint")
        and latest.get("gate_decision") == gate
    )
    eligible = (
        freshness_view["state"] == "fresh"
        and projection.state == "ready"
        and m4.task_applicable
        and packet_closed_in_projection
    )
    return {
        "submission_allowed": eligible,
        "allowed_decisions": tuple(allowed) if eligible else (),
        "gate": gate,
        "reason": None if eligible else "fresh closed Task Assurance is required",
        "current": copy.deepcopy(projection.projection.get("decision"))
        if isinstance(projection.projection, dict)
        else None,
    }


def _history(records: list[EventRecord]) -> tuple[dict, ...]:
    rows = []
    for record in records:
        payload = record.payload
        references = {
            key: copy.deepcopy(payload[key])
            for key in (
                "evidence_id",
                "packet_fingerprint",
                "assurance_packet_fingerprint",
                "gate_fingerprint",
                "gate_decision",
                "decision",
                "evidence_refs",
            )
            if key in payload
        }
        rows.append(
            {
                "sequence": record.sequence,
                "event_id": record.event_id,
                "event_type": record.event_type,
                "occurred_at": record.occurred_at,
                "redaction_status": record.redaction_status,
                "references": references,
            }
        )
    return tuple(rows)


def _unavailable_evidence(task_id: str, evidence_id: str, reason: str) -> EvidenceView:
    return EvidenceView(
        evidence_id=evidence_id,
        reference_kind="unavailable",
        task_id=task_id,
        result="unknown",
        basis="unobserved",
        content_hash=None,
        content_size=None,
        redaction_status="reference_only",
        raw_available=False,
        metadata={"reason": reason},
    )


def _evidence_views(
    evidence_store: EvidenceStore,
    task_id: str,
    assurance_packet: dict | None,
) -> tuple[EvidenceView, ...]:
    store_ids = {record.evidence_id for record in evidence_store.list_for_task(task_id)}
    logical_ids = set(
        assurance_packet.get("evidence_refs", [])
        if isinstance(assurance_packet, dict)
        else []
    )
    rows = []
    for evidence_id in sorted(store_ids | logical_ids):
        try:
            view, _ = resolve_evidence(
                evidence_store,
                task_id=task_id,
                evidence_id=evidence_id,
                assurance_packet=assurance_packet,
            )
        except (OSError, ValueError) as error:
            view = _unavailable_evidence(task_id, evidence_id, str(error))
        rows.append(view)
    return tuple(rows)


def assemble_task_review(
    *,
    task: TaskIdentity,
    events: EventLog,
    projection: ProjectionStatus,
    freshness: Freshness,
    evidence_store: EvidenceStore,
    baseline: dict | None,
    context_status: dict | None,
    execution_contract: dict | None,
    m3_packet: dict | None,
    assurance_packet: dict | None,
    guarantee_report: dict | None,
    assembled_at: str,
) -> TaskReviewView:
    m3 = validate_m3_source(task=task, packet=m3_packet) if m3_packet is not None else _unavailable("m3")
    m4 = validate_m4_source(task=task, packet=assurance_packet) if assurance_packet is not None else _unavailable("m4")
    freshness_view = _freshness_view(task, projection, freshness)
    evidence_records = evidence_store.list_for_task(task.task_id)
    direct = _direct_evidence(evidence_store, evidence_records, task)
    guarantee_matches = _matching_guarantee(
        task, guarantee_report, evidence_store
    )
    event_records = events.list_for_task(task.task_id)
    m2 = {
        kind: _m2_source(
            task=task, artifact=artifact, kind=kind, store=evidence_store,
            records=evidence_records, events=event_records,
            execution_contract=execution_contract, assurance_packet=assurance_packet, m4=m4,
        ) if events.catalog is evidence_store.catalog else "unobserved"
        for kind, artifact in (("project_baseline", baseline), ("context_status", context_status))
    }
    return TaskReviewView(
        task=_task_identity(task),
        summary=_source_backed_summary(task, execution_contract, assurance_packet, m3, m4),
        freshness=freshness_view,
        completeness=_completeness(
            task,
            m3,
            m4,
            m2,
            execution_contract,
            assurance_packet,
            guarantee_matches,
            direct,
        ),
        diagram=_bounded_diagram(
            task, baseline, execution_contract, assurance_packet, m4,
            m2["project_baseline"] == "closed",
        ),
        relations=_relations(assurance_packet, m4),
        verification=_verification(assurance_packet, m4, direct),
        guarantees=_guarantees(guarantee_report, guarantee_matches),
        harness=_harness(task, baseline, context_status, m3_packet, m3, m2),
        assurance=_assurance(assurance_packet, m4),
        decision=_decision(projection, freshness_view, assurance_packet, m4),
        history=_history(event_records),
        evidence=_evidence_views(evidence_store, task.task_id, assurance_packet),
        assembled_at=_iso_time(assembled_at),
    )

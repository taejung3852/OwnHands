from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime

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


def _matching_guarantee(task: TaskIdentity, report: dict | None) -> bool:
    if not isinstance(report, dict) or report.get("report_version") != "1.0":
        return False
    identity = report.get("task")
    return (
        _task_matches(task, identity)
        and isinstance(identity, dict)
        and identity.get("target_commit") == task.commit
        and isinstance(report.get("claim_results"), list)
        and bool(report["claim_results"])
    )


def _direct_evidence(
    store: EvidenceStore, records: list[EvidenceRecord]
) -> EvidenceRecord | None:
    candidates = [
        record
        for record in records
        if record.evidence_type == "direct_feature_probe"
        and record.basis == "observed"
        and record.result in {"pass", "fail", "inconclusive"}
        and record.fields.get("human_observation") is True
    ]
    for record in reversed(candidates):
        try:
            store.read_content(record.evidence_id)
        except (OSError, ValueError):
            continue
        return record
    return None


def _completeness(
    task: TaskIdentity,
    m3: SourceClosure,
    m4: SourceClosure,
    baseline: dict | None,
    context_status: dict | None,
    execution_contract: dict | None,
    assurance_packet: dict | None,
    guarantee_matches: bool,
    direct: EvidenceRecord | None,
) -> dict:
    missing = []
    if not isinstance(baseline, dict) or not baseline.get("baseline_id") or not baseline.get("fingerprint"):
        missing.append("project_baseline")
    elif any(
        field in baseline and baseline[field] != getattr(task, field)
        for field in ("project_id", "worktree_id", "environment_ref")
    ):
        missing.append("project_baseline")
    if not isinstance(context_status, dict) or not context_status:
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


def _bounded_diagram(assurance_packet: dict | None, m4: SourceClosure) -> dict:
    if m4.status != "closed" or not isinstance(assurance_packet, dict):
        return {"state": "unobserved", "kind": None, "nodes": (), "edges": ()}
    relations = assurance_packet["impact"].get("relations", [])
    if not relations:
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
    return tuple(sorted(rows, key=lambda item: (item["priority"], item["relation_id"])))


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


def _guarantees(task: TaskIdentity, report: dict | None) -> tuple[dict, ...]:
    if not _matching_guarantee(task, report):
        return (
            {
                "claim_id": "task_guarantees",
                "status": "not_evaluated",
                "verdict": None,
                "basis": "unobserved",
                "evidence_refs": (),
            },
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
                "basis": "observed",
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


def _artifact_ref(value: dict | None, id_field: str) -> dict:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    return {
        "status": "observed",
        id_field: value.get(id_field),
        "fingerprint": value.get("fingerprint"),
    }


def _harness(
    baseline: dict | None,
    context_status: dict | None,
    m3_packet: dict | None,
    m3: SourceClosure,
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
        "baseline": _artifact_ref(baseline, "baseline_id"),
        "context_status": _artifact_ref(context_status, "status_id"),
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
    direct = _direct_evidence(evidence_store, evidence_records)
    guarantee_matches = _matching_guarantee(task, guarantee_report)
    return TaskReviewView(
        task=_task_identity(task),
        summary=_source_backed_summary(task, execution_contract, assurance_packet, m3, m4),
        freshness=freshness_view,
        completeness=_completeness(
            task,
            m3,
            m4,
            baseline,
            context_status,
            execution_contract,
            assurance_packet,
            guarantee_matches,
            direct,
        ),
        diagram=_bounded_diagram(assurance_packet, m4),
        relations=_relations(assurance_packet, m4),
        verification=_verification(assurance_packet, m4, direct),
        guarantees=_guarantees(task, guarantee_report),
        harness=_harness(baseline, context_status, m3_packet, m3),
        assurance=_assurance(assurance_packet, m4),
        decision=_decision(projection, freshness_view, assurance_packet, m4),
        history=_history(events.list_for_task(task.task_id)),
        evidence=_evidence_views(evidence_store, task.task_id, assurance_packet),
        assembled_at=_iso_time(assembled_at),
    )

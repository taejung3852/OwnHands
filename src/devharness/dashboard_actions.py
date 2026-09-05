from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from .dashboard_events import _record_task_decision
from .dashboard_security import require_opaque_identifier
from .dashboard_view import TaskReviewView
from .evidence import EvidenceDraft, EvidenceRecord, EvidenceStore
from .events import EventLog, EventRecord
from .identity import IdentityRegistry


_RESULTS = {"pass", "fail", "not_run", "inconclusive"}
_BASES = {"observed", "inferred", "unobserved"}


@dataclass(frozen=True)
class ValidationRequest:
    task_id: str
    subject_ref: str
    expected: str
    input_summary: str


@dataclass(frozen=True)
class ValidationObservation:
    result: str
    basis: str
    actual: str
    generated_files: tuple[str, ...]
    tool_error: str | None
    human_observation: str | None
    generated_output: str | None = None


class ValidationAdapter(Protocol):
    adapter_ref: str

    def validate(self, request: ValidationRequest) -> ValidationObservation: ...


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _optional_text(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name)


def _timestamp(value: object, name: str) -> str:
    text = _text(value, name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return text


def _validation_request(request: ValidationRequest) -> ValidationRequest:
    if not isinstance(request, ValidationRequest):
        raise TypeError("request must be a ValidationRequest")
    require_opaque_identifier(request.task_id, "task_id")
    require_opaque_identifier(request.subject_ref, "subject_ref")
    if not (
        request.subject_ref == "subject:hwpx"
        or request.subject_ref.startswith("subject:hwpx:")
    ):
        raise ValueError("subject_ref must identify an HWPX subject")
    _text(request.expected, "expected")
    _text(request.input_summary, "input_summary")
    return request


def _validation_observation(value: object) -> ValidationObservation:
    if not isinstance(value, ValidationObservation):
        raise ValueError("adapter must return a ValidationObservation")
    if value.result not in _RESULTS:
        raise ValueError("observation result is invalid")
    if value.basis not in _BASES:
        raise ValueError("observation basis is invalid")
    if value.result == "not_run" and value.basis != "unobserved":
        raise ValueError("not_run observation must be unobserved")
    _text(value.actual, "actual")
    if not isinstance(value.generated_files, tuple) or any(
        not isinstance(item, str) or not item.strip() for item in value.generated_files
    ):
        raise ValueError("generated_files must be a tuple of non-empty strings")
    _optional_text(value.generated_output, "generated_output")
    _optional_text(value.tool_error, "tool_error")
    _optional_text(value.human_observation, "human_observation")
    if value.result != "not_run" and not (
        value.generated_files or value.generated_output or value.tool_error
    ):
        raise ValueError(
            "adapter observation requires generated output, generated files, or tool error"
        )
    return value


def _adapter_reference(adapter: ValidationAdapter) -> str:
    reference = _text(getattr(adapter, "adapter_ref", None), "adapter_ref")
    if re.fullmatch(r"adapter:hwpx(?::[A-Za-z0-9_.-]+)*", reference) is None:
        raise ValueError("HWPX subject requires an exact HWPX adapter")
    return reference


def _allowlisted_observation(
    request: ValidationRequest,
    observation: ValidationObservation,
    *,
    adapter_ref: str,
    environment: str,
    target_commit: str,
    occurred_at: str,
) -> dict:
    return {
        "adapter_ref": adapter_ref,
        "input": request.input_summary,
        "expected": request.expected,
        "actual": observation.actual,
        "environment": environment,
        "generated_files": list(observation.generated_files),
        "generated_output": observation.generated_output,
        "tool_error": observation.tool_error,
        "human_observation": observation.human_observation,
        "occurred_at": occurred_at,
        "task_ref": request.task_id,
        "target_commit": target_commit,
    }


def run_feature_validation(
    *,
    adapter: ValidationAdapter | None,
    request: ValidationRequest,
    evidence_store: EvidenceStore,
    evidence_id: str,
    occurred_at: str,
) -> EvidenceRecord:
    request = _validation_request(request)
    require_opaque_identifier(evidence_id, "evidence_id")
    occurred_at = _timestamp(occurred_at, "occurred_at")
    task = IdentityRegistry(evidence_store.catalog).get_task(request.task_id)
    if adapter is None:
        adapter_ref = "adapter:hwpx:unregistered"
        observation = ValidationObservation(
            result="not_run",
            basis="unobserved",
            actual="No registered adapter or human observation",
            generated_files=(),
            generated_output=None,
            tool_error=None,
            human_observation=None,
        )
        collection_method = "dashboard-feature-validation-unobserved"
    else:
        adapter_ref = _adapter_reference(adapter)
        observation = _validation_observation(adapter.validate(request))
        if observation.human_observation is None:
            observation = replace(
                observation,
                result="not_run",
                basis="unobserved",
            )
        collection_method = f"dashboard-feature-adapter:{adapter_ref}"
    fields = _allowlisted_observation(
        request,
        observation,
        adapter_ref=adapter_ref,
        environment=task.environment_ref,
        target_commit=task.commit,
        occurred_at=occurred_at,
    )
    content = json.dumps(
        fields,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return evidence_store.put(
        EvidenceDraft(
            evidence_id=evidence_id,
            task_id=request.task_id,
            requirement_id="M5-06",
            evidence_type="direct_feature_probe",
            subject_ref=request.subject_ref,
            exact_scope=request.input_summary,
            result=observation.result,
            basis=observation.basis,
            fields=fields,
            content=content,
            collection_method=collection_method,
            redaction_status="redacted",
        ),
        lambda payload: payload,
    )


def _form_text(form: Mapping[str, str], name: str) -> str:
    return _text(form.get(name), name)


def _form_references(
    form: Mapping[str, str],
    name: str,
    *,
    required: bool,
    opaque: bool,
) -> tuple[str, ...]:
    value = form.get(name)
    if not isinstance(value, str):
        if required:
            raise ValueError(f"{name} must be a non-empty string")
        return ()
    references = tuple(item.strip() for item in value.splitlines() if item.strip())
    if required and not references:
        raise ValueError(f"{name} must contain at least one reference")
    if len(references) != len(set(references)):
        raise ValueError(f"{name} must not contain duplicates")
    if opaque:
        for reference in references:
            require_opaque_identifier(reference, name)
    return references


def submit_task_decision(
    *,
    view: TaskReviewView,
    events: EventLog,
    form: Mapping[str, str],
    event_id: str,
    occurred_at: str,
) -> EventRecord:
    if not isinstance(form, Mapping):
        raise TypeError("form must be a mapping")
    if not isinstance(view.task, dict):
        raise ValueError("Task view is invalid")
    task_id = _form_text(form, "task_id")
    require_opaque_identifier(task_id, "task_id")
    if task_id != view.task.get("task_id"):
        raise ValueError("Decision Task does not match the current view")
    canonical_task = IdentityRegistry(events.catalog).get_task(task_id)
    for name, expected in (
        ("project_id", canonical_task.project_id),
        ("worktree_id", canonical_task.worktree_id),
        ("mode", canonical_task.mode),
        ("commit", canonical_task.commit),
        ("branch", canonical_task.branch),
        ("environment_ref", canonical_task.environment_ref),
    ):
        if name in view.task and view.task[name] != expected:
            raise ValueError(f"Decision Task {name} is stale")

    freshness = view.freshness if isinstance(view.freshness, dict) else {}
    if (
        freshness.get("state") != "fresh"
        or freshness.get("projection_state") != "ready"
        or not isinstance(freshness.get("event_head"), int)
        or isinstance(freshness.get("event_head"), bool)
        or not isinstance(freshness.get("projected_sequence"), int)
        or isinstance(freshness.get("projected_sequence"), bool)
        or freshness.get("event_head") != freshness.get("projected_sequence")
        or not view.decision.get("submission_allowed")
    ):
        raise ValueError("stale Dashboard view cannot record a Decision")
    assurance = view.assurance if isinstance(view.assurance, dict) else {}
    source = assurance.get("source") if isinstance(assurance.get("source"), dict) else {}
    gate = assurance.get("gate") if isinstance(assurance.get("gate"), dict) else {}
    selected = _form_text(form, "decision")
    current_gate = gate.get("decision")
    if current_gate == "hard_block" and selected in {"accept", "risk_acceptance"}:
        raise ValueError("Hard Block cannot be accepted or risk accepted")
    if selected not in view.decision.get("allowed_decisions", ()):
        raise ValueError("Decision is not allowed by the current Gate")

    packet_fingerprint = _form_text(form, "assurance_packet_fingerprint")
    gate_fingerprint = _form_text(form, "gate_fingerprint")
    gate_decision = _form_text(form, "gate_decision")
    if packet_fingerprint != source.get("fingerprint"):
        raise ValueError("Decision Assurance packet is stale")
    if gate_fingerprint != gate.get("fingerprint") or gate_decision != current_gate:
        raise ValueError("Decision Gate is stale")
    if source.get("status") != "closed" or source.get("task_applicable") is not True:
        raise ValueError("Decision Assurance must be closed and applicable to this Task")
    if view.decision.get("gate") != current_gate:
        raise ValueError("Decision Gate is stale")

    decision_source = _form_text(form, "decision_source")
    reason = _form_text(form, "reason")
    actor_ref = _form_text(form, "actor_ref")
    follow_up = _form_text(form, "follow_up")
    residual_risks = _form_references(
        form, "residual_risks", required=False, opaque=False
    )
    evidence_refs = _form_references(
        form, "evidence_refs", required=True, opaque=True
    )
    if selected == "risk_acceptance" and (
        current_gate != "soft_block"
        or decision_source != "product_authority"
        or not residual_risks
    ):
        raise ValueError(
            "risk acceptance requires exact Soft Block, product_authority, reason, and residual risk"
        )

    return _record_task_decision(
        events,
        values={
            "event_id": _text(event_id, "event_id"),
            "task_id": task_id,
            "assurance_packet_fingerprint": packet_fingerprint,
            "gate_fingerprint": gate_fingerprint,
            "gate_decision": gate_decision,
            "decision": selected,
            "decision_source": decision_source,
            "actor_ref": actor_ref,
            "reason": reason,
            "residual_risks": residual_risks,
            "follow_up": follow_up,
            "evidence_refs": evidence_refs,
            "occurred_at": _timestamp(occurred_at, "occurred_at"),
        },
        expected_event_head=freshness["event_head"],
        expected_projected_sequence=freshness["projected_sequence"],
    )
